"""
Dictionary Import Service

Imports vocabulary from external sources (Lee dict, Matsushita dict) via Google Sheets.
"""

import re
from typing import Dict, List, Optional

import pandas as pd
import structlog

from app.services.lexical_network.column_mappings import (
    LEE_DICT_MAPPING,
    MATSUSHITA_DICT_MAPPING,
    normalize_difficulty,
    normalize_etymology,
    normalize_pos,
    parse_bunrui_hierarchy,
)
from app.services.lexical_network.pos_mapper import (
    map_lee_pos_to_unidic,
    map_matsushita_pos_to_unidic,
    should_update_canonical_pos,
)

logger = structlog.get_logger()


class DictionaryImportService:
    """Service for importing vocabulary dictionaries."""
    
    async def import_from_google_sheets(
        self,
        neo4j_session,
        sheet_url: str,
        source_name: str,
        column_mapping: Dict[str, str],
        sheet_name: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Import vocabulary from Google Sheets.
        
        Args:
            neo4j_session: Neo4j async session
            sheet_url: Google Sheets URL
            source_name: Source identifier ("lee_dict", "matsushita_dict")
            column_mapping: Map from sheet columns to Neo4j properties
            sheet_name: Optional sheet name if multiple sheets
            
        Returns:
            Import statistics
        """
        stats = {"imported": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        try:
            # Convert to CSV export URL
            csv_url = self._to_csv_url(sheet_url, sheet_name)
            
            # Read the sheet
            logger.info("Reading Google Sheet", url=csv_url)
            df = pd.read_csv(csv_url)
            
            logger.info("Sheet loaded", rows=len(df), columns=list(df.columns))
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    # Map columns
                    word_data = {}
                    for sheet_col, neo4j_prop in column_mapping.items():
                        if sheet_col in row and pd.notna(row[sheet_col]):
                            value = str(row[sheet_col]).strip()
                            if value:
                                # Normalize specific fields
                                if neo4j_prop == "difficulty_level" or neo4j_prop == "lee_difficulty_level":
                                    # For Lee: use source-specific fields
                                    if source_name == "lee":
                                        word_data["lee_difficulty_level"] = value
                                        word_data["lee_difficulty_numeric"] = normalize_difficulty(value)
                                    # Also set legacy fields for backward compatibility
                                    word_data["difficulty_numeric"] = normalize_difficulty(value)
                                    word_data["difficulty_level"] = value
                                elif neo4j_prop == "matsushita_difficulty":
                                    # For Matsushita: use source-specific fields
                                    word_data["matsushita_difficulty"] = value
                                    word_data["matsushita_difficulty_numeric"] = normalize_difficulty(value)
                                    # Also set legacy fields
                                    word_data["difficulty_numeric"] = normalize_difficulty(value)
                                    word_data["difficulty_level"] = value
                                elif neo4j_prop == "pos_primary":
                                    # Store original POS
                                    word_data["pos_primary"] = normalize_pos(value)
                                    # Map to canonical UniDic format
                                    if source_name == "lee" or source_name == "lee_dict":
                                        # Get detailed POS if available
                                        pos_detailed = None
                                        if "品詞2(詳細)" in row and pd.notna(row["品詞2(詳細)"]):
                                            pos_detailed = str(row["品詞2(詳細)"]).strip()
                                        elif "品詞2" in row and pd.notna(row["品詞2"]):
                                            pos_detailed = str(row["品詞2"]).strip()
                                        
                                        canonical = map_lee_pos_to_unidic(value, pos_detailed)
                                        # Only set canonical if higher priority than existing
                                        word_data["_canonical_pos"] = canonical
                                        word_data["_pos_source"] = "lee"
                                    elif source_name == "matsushita" or source_name == "matsushita_dict":
                                        canonical = map_matsushita_pos_to_unidic(value)
                                        word_data["_canonical_pos"] = canonical
                                        word_data["_pos_source"] = "matsushita"
                                elif neo4j_prop == "pos_detailed":
                                    # Store detailed POS (for Lee)
                                    word_data["pos_detailed"] = value
                                elif neo4j_prop == "etymology":
                                    word_data["etymology"] = normalize_etymology(value)
                                elif neo4j_prop == "bunrui_number":
                                    word_data["bunrui_number"] = value
                                    # Parse bunrui hierarchy
                                    hierarchy = parse_bunrui_hierarchy(value)
                                    if hierarchy:
                                        word_data.update(hierarchy)
                                else:
                                    word_data[neo4j_prop] = value
                    
                    # Require standard_orthography
                    if not word_data.get("standard_orthography"):
                        stats["skipped"] += 1
                        continue
                    
                    # Handle canonical POS (extract from _canonical_pos if present)
                    canonical_pos = word_data.pop("_canonical_pos", None)
                    pos_source = word_data.pop("_pos_source", None)
                    
                    # Separate id fields that shouldn't be updated on match
                    create_props = word_data.copy()
                    update_props = {k: v for k, v in word_data.items() if not k.endswith("_id")}
                    
                    # Merge into Neo4j with source tracking
                    # Use a two-step approach: first merge, then update canonical POS if needed
                    query = """
                    MERGE (w:Word {standard_orthography: $standard_orthography})
                    ON CREATE SET
                        w += $create_props,
                        w.source = $source,
                        w.sources = [$source],
                        w.created_at = datetime()
                    ON MATCH SET
                        w += $update_props,
                        w.sources = CASE 
                            WHEN w.sources IS NULL THEN [$source]
                            WHEN NOT $source IN w.sources THEN w.sources + [$source]
                            ELSE w.sources
                        END,
                        w.updated_at = datetime()
                    RETURN 
                        CASE WHEN w.created_at = datetime() THEN 'created' ELSE 'updated' END AS action,
                        w.pos_source AS existing_pos_source
                    """
                    
                    result = await neo4j_session.run(
                        query,
                        standard_orthography=word_data["standard_orthography"],
                        create_props=create_props,
                        update_props=update_props,
                        source=source_name,
                    )
                    
                    record = await result.single()
                    
                    # Update canonical POS if we have it and it's higher priority
                    if canonical_pos and pos_source and record:
                        from app.services.lexical_network.pos_mapper import get_pos_priority, should_update_canonical_pos
                        existing_pos_source = record.get("existing_pos_source")
                        
                        if should_update_canonical_pos(existing_pos_source, pos_source):
                            update_query = """
                            MATCH (w:Word {standard_orthography: $standard_orthography})
                            SET w.pos1 = $pos1,
                                w.pos2 = $pos2,
                                w.pos3 = $pos3,
                                w.pos4 = $pos4,
                                w.pos_primary_norm = $pos_primary_norm,
                                w.pos_source = $pos_source,
                                w.pos_confidence = $pos_confidence,
                                w.updated_at = datetime()
                            """
                            await neo4j_session.run(
                                update_query,
                                standard_orthography=word_data["standard_orthography"],
                                pos1=canonical_pos.get("pos1"),
                                pos2=canonical_pos.get("pos2"),
                                pos3=canonical_pos.get("pos3"),
                                pos4=canonical_pos.get("pos4"),
                                pos_primary_norm=canonical_pos.get("pos_primary_norm"),
                                pos_source=pos_source,
                                pos_confidence=1.0,  # Dictionary sources have full confidence
                            )
                    
                    if record:
                    
                    record = await result.single()
                    if record:
                        action = record.get("action", "updated")
                        if action == "created":
                            stats["imported"] += 1
                        else:
                            stats["updated"] += 1
                    
                    # Progress logging
                    if (stats["imported"] + stats["updated"]) % 100 == 0:
                        logger.info(
                            "Import progress",
                            imported=stats["imported"],
                            updated=stats["updated"],
                            row=idx,
                        )
                        
                except Exception as e:
                    logger.error("Import error", row=idx, error=str(e))
                    stats["errors"] += 1
            
            logger.info("Import completed", **stats)
            return stats
            
        except Exception as e:
            logger.error("Failed to import dictionary", source=source_name, error=str(e))
            raise
    
    async def check_missing_words(
        self,
        neo4j_session,
        sheet_url: str,
        column_mapping: Dict[str, str],
    ) -> Dict[str, any]:
        """
        Check which words from sheet are missing in Neo4j.
        
        Args:
            neo4j_session: Neo4j async session
            sheet_url: Google Sheets URL
            column_mapping: Column mapping
            
        Returns:
            Report with missing words
        """
        try:
            csv_url = self._to_csv_url(sheet_url)
            df = pd.read_csv(csv_url)
            
            sheet_words = set()
            for _, row in df.iterrows():
                if "語彙" in column_mapping:
                    col_name = [k for k, v in column_mapping.items() if v == "standard_orthography"][0]
                    if col_name in row and pd.notna(row[col_name]):
                        word = str(row[col_name]).strip()
                        if word:
                            sheet_words.add(word)
            
            # Check which are in Neo4j
            query = """
            MATCH (w:Word)
            WHERE w.standard_orthography IN $words
            RETURN w.standard_orthography AS word
            """
            result = await neo4j_session.run(query, words=list(sheet_words))
            existing_words = {record["word"] for record in await result.data()}
            
            missing_words = sheet_words - existing_words
            
            return {
                "total_in_sheet": len(sheet_words),
                "existing_in_neo4j": len(existing_words),
                "missing": len(missing_words),
                "missing_words": list(missing_words)[:100],  # Limit to 100
            }
        except Exception as e:
            logger.error("Failed to check missing words", error=str(e))
            raise
    
    async def merge_dictionaries(
        self,
        neo4j_session,
        primary_source: str,
        secondary_source: str,
    ) -> Dict[str, int]:
        """
        Merge words from secondary into primary.
        
        Rules:
        - Primary source data takes precedence
        - Secondary fills in missing fields
        - Track source attribution
        
        Args:
            neo4j_session: Neo4j async session
            primary_source: Primary source name
            secondary_source: Secondary source name
            
        Returns:
            Merge statistics
        """
        stats = {"merged": 0, "updated": 0, "errors": 0}
        
        query = """
        MATCH (w:Word)
        WHERE w.source = $secondary_source
        WITH w
        MATCH (primary:Word {standard_orthography: w.standard_orthography})
        WHERE primary.source = $primary_source
        SET primary += w,
            primary.source_merged = [$primary_source, $secondary_source],
            primary.updated_at = datetime()
        RETURN count(*) AS merged
        """
        
        try:
            result = await neo4j_session.run(
                query, primary_source=primary_source, secondary_source=secondary_source
            )
            record = await result.single()
            stats["merged"] = record.get("merged", 0) if record else 0
        except Exception as e:
            logger.error("Failed to merge dictionaries", error=str(e))
            stats["errors"] += 1
        
        return stats
    
    def _to_csv_url(self, sheet_url: str, sheet_name: Optional[str] = None) -> str:
        """
        Convert Google Sheets URL to CSV export URL.
        
        Args:
            sheet_url: Google Sheets URL
            sheet_name: Optional sheet name
            
        Returns:
            CSV export URL
        """
        # Extract sheet ID
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if not match:
            raise ValueError(f"Invalid Google Sheets URL: {sheet_url}")
        
        sheet_id = match.group(1)
        base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        if sheet_name:
            base_url += f"&gid={sheet_name}"
        
        return base_url
