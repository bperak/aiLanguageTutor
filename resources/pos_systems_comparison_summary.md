# POS Systems Comparison: Lee李 vs UniDic

## Overview

This document compares the Part of Speech (POS) classification systems used in:
- **Lee李 分類語彙表学習者用goi** (Lee李 vocabulary list)
- **UniDic** (Japanese morphological analysis system)

## Key Differences

### 1. **System Complexity**
- **Lee李**: 21 main POS categories, 242 detailed categories
- **UniDic**: 7 main POS categories, more standardized

### 2. **Verb Classification**
**Lee李** uses **conjugation-based classification**:
- `動詞1類` (Group 1 verbs) - 1,311 entries
- `動詞2類` (Group 2 verbs) - 645 entries  
- `動詞3類` (Group 3 verbs) - 197 entries

**UniDic** uses **morphological classification**:
- `動詞` (Verb) - all verb types combined
- Subcategories: `一般`, `非自立可能`

### 3. **Adjective Classification**
**Lee李** distinguishes:
- `イ形容詞` (i-adjectives) - 277 entries
- `ナ形容詞` (na-adjectives) - 502 entries

**UniDic** distinguishes:
- `形容詞` (Adjective) - for i-adjectives
- `形状詞` (Adjectival noun) - for na-adjectives

### 4. **Noun Classification**
**Lee李**: 
- `名詞` (Noun) - 13,712 entries (largest category)
- Very detailed subcategories

**UniDic**:
- `名詞` (Noun) - with subcategories like `普通名詞`

## Mapping Table

| Lee李 POS1 | UniDic POS1 | Notes |
|------------|-------------|-------|
| 名詞 | 名詞 | Direct mapping |
| 動詞1類 | 動詞 | All verb groups → 動詞 |
| 動詞2類 | 動詞 | All verb groups → 動詞 |
| 動詞3類 | 動詞 | All verb groups → 動詞 |
| イ形容詞 | 形容詞 | Direct mapping |
| ナ形容詞 | 形状詞 | na-adjectives → adjectival nouns |
| 副詞 | 副詞 | Direct mapping |
| 感動詞 | 感動詞 | Direct mapping |
| 接頭辞 | 接頭辞 | Direct mapping |
| 接尾辞 | 名詞 | Often treated as noun in UniDic |
| 代名詞 | 代名詞 | Direct mapping |
| 接続詞 | 名詞 | Often treated as noun in UniDic |
| 連体詞 | 名詞 | Often treated as noun in UniDic |
| 定型表現 | 名詞 | Often treated as noun in UniDic |

## Key Insights

### 1. **Lee李 is More Pedagogical**
- Designed for language learners
- Verb groups help with conjugation patterns
- Clear distinction between i-adjectives and na-adjectives

### 2. **UniDic is More Linguistic**
- Based on morphological analysis
- More standardized POS tags
- Better for computational processing

### 3. **Mapping Challenges**
- **Many-to-one mappings**: Lee李's detailed categories often map to single UniDic categories
- **Cross-category mappings**: Some Lee李 categories span multiple UniDic categories
- **Context-dependent**: Same word can have different POS in different contexts

## Practical Implications

### For AI Language Tutor:

1. **Use Lee李 for Learning**: 
   - Verb conjugation patterns
   - Adjective types for grammar rules
   - Learner-friendly categories

2. **Use UniDic for Analysis**:
   - Morphological analysis
   - Pronunciation and accent
   - Computational processing

3. **Hybrid Approach**:
   - Map UniDic analysis to Lee李 categories
   - Provide both systems for comprehensive learning
   - Use UniDic for advanced features (accent, pronunciation)

## Recommendations

1. **Keep both systems** in the database
2. **Create mapping functions** to convert between systems
3. **Use Lee李 categories** for user-facing features
4. **Use UniDic data** for technical analysis and pronunciation
5. **Provide explanations** of both systems to advanced learners

## Sample Mappings

| Word | Lee李 POS1 | Lee李 POS2 | UniDic POS1 | UniDic POS2 |
|------|------------|------------|-------------|-------------|
| 愛 | 名詞 | 名詞-普通名詞-一般 | 接頭辞 | (empty) |
| 行く | 動詞1類 | 動詞-一般 | 動詞 | 一般 |
| 美しい | イ形容詞 | 形容詞-一般 | 形容詞 | 一般 |
| 静か | ナ形容詞 | 形容詞-一般 | 形状詞 | 一般 |
| とても | 副詞 | 副詞 | 副詞 | (empty) |
| こんにちは | 感動詞 | 感動詞-一般 | 感動詞 | 一般 |

This comparison shows that while both systems serve different purposes, they can complement each other effectively in an AI language learning system.
