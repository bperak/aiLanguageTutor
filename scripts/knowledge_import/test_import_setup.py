"""
Test script to validate the enhanced import setup.
Checks data files and dependencies before running full import.
"""

import os
import sys
from pathlib import Path
import pickle
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a file exists and is readable."""
    if file_path.exists():
        print(f"✅ {description}: Found at {file_path}")
        return True
    else:
        print(f"❌ {description}: Not found at {file_path}")
        return False


def analyze_lee_vocabulary(file_path: Path) -> dict:
    """Analyze Lee's vocabulary file structure."""
    try:
        df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
        
        analysis = {
            'total_entries': len(df),
            'columns': list(df.columns),
            'difficulty_levels': df['Level 語彙の難易度'].value_counts().to_dict(),
            'etymologies': df['語種'].value_counts().to_dict(),
            'sample_entries': df.head(3).to_dict('records')
        }
        
        print(f"✅ Lee's Vocabulary Analysis:")
        print(f"   - Total entries: {analysis['total_entries']:,}")
        print(f"   - Difficulty levels: {len(analysis['difficulty_levels'])}")
        print(f"   - Etymology types: {len(analysis['etymologies'])}")
        print(f"   - Sample entry: {analysis['sample_entries'][0]['Standard orthography (kanji or other) 標準的な表記']}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing Lee's vocabulary: {e}")
        return {}


def analyze_networkx_graph(file_path: Path) -> dict:
    """Analyze NetworkX graph structure."""
    try:
        with open(file_path, 'rb') as f:
            graph = pickle.load(f)
        
        # Sample node and edge data
        sample_nodes = list(graph.nodes(data=True))[:3]
        sample_edges = list(graph.edges(data=True))[:3]
        
        analysis = {
            'total_nodes': graph.number_of_nodes(),
            'total_edges': graph.number_of_edges(),
            'sample_nodes': sample_nodes,
            'sample_edges': sample_edges
        }
        
        print(f"✅ NetworkX Graph Analysis:")
        print(f"   - Total nodes: {analysis['total_nodes']:,}")
        print(f"   - Total edges: {analysis['total_edges']:,}")
        print(f"   - Sample node: {sample_nodes[0][0]} -> {sample_nodes[0][1].get('translation', 'N/A')}")
        print(f"   - Sample edge: {sample_edges[0][0]} -> {sample_edges[0][1]} (strength: {sample_edges[0][2].get('synonym_strength', 'N/A')})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing NetworkX graph: {e}")
        return {}


def check_environment_variables():
    """Check required environment variables."""
    required_vars = [
        'NEO4J_URI',
        'NEO4J_USERNAME', 
        'NEO4J_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set these in your .env file or environment")
        return False
    else:
        print("✅ All required environment variables are set")
        return True


def main():
    """Main validation function."""
    print("🔍 Enhanced Import Setup Validation")
    print("=" * 50)
    
    # Check data files
    base_path = Path("resources")
    
    files_ok = True
    files_ok &= check_file_exists(
        base_path / "Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv",
        "Lee's Vocabulary Database"
    )
    files_ok &= check_file_exists(
        base_path / "G_synonyms_2024_09_18.pickle", 
        "NetworkX Synonym Graph"
    )
    
    print()
    
    # Analyze data if files exist
    if files_ok:
        print("📊 Data Analysis")
        print("-" * 30)
        
        lee_analysis = analyze_lee_vocabulary(
            base_path / "Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv"
        )
        print()
        
        networkx_analysis = analyze_networkx_graph(
            base_path / "G_synonyms_2024_09_18.pickle"
        )
        print()
    
    # Check environment
    print("🔧 Environment Check")
    print("-" * 30)
    env_ok = check_environment_variables()
    print()
    
    # Check import scripts
    print("📝 Import Scripts Check")
    print("-" * 30)
    
    scripts_path = Path("scripts/knowledge_import/enhanced_importers")
    scripts_ok = True
    scripts_ok &= check_file_exists(scripts_path / "lee_vocabulary_importer.py", "Lee Vocabulary Importer")
    scripts_ok &= check_file_exists(scripts_path / "networkx_graph_importer.py", "NetworkX Graph Importer")
    scripts_ok &= check_file_exists(scripts_path / "unified_import_orchestrator.py", "Unified Import Orchestrator")
    
    print()
    
    # Final assessment
    print("🎯 Readiness Assessment")
    print("=" * 50)
    
    if files_ok and env_ok and scripts_ok:
        print("✅ READY TO PROCEED WITH ENHANCED IMPORT!")
        print(f"   - Will import {lee_analysis.get('total_entries', 0):,} vocabulary entries")
        print(f"   - Will import {networkx_analysis.get('total_nodes', 0):,} graph nodes")
        print(f"   - Will create {networkx_analysis.get('total_edges', 0):,} synonym relationships")
        print()
        print("🚀 Next steps:")
        print("   1. Ensure Neo4j is running (docker-compose up -d)")
        print("   2. Run: python scripts/knowledge_import/enhanced_importers/unified_import_orchestrator.py")
        return True
    else:
        print("❌ NOT READY - Please fix the issues above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
