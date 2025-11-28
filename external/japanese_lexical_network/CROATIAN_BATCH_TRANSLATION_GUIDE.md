# Croatian Batch Translation Guide

## 🚀 **How to Use the Croatian Batch Translation Scripts**

This guide explains how to use the batch translation scripts to add English translations to Croatian nodes in the lexical graph.

## 📋 **Prerequisites**

1. **Virtual Environment**: Make sure you have the virtual environment activated:
   ```bash
   venv\Scripts\Activate.ps1
   ```

2. **Required Dependencies**: All required packages should be installed via `requirements.txt`

3. **API Access**: Ensure you have valid Gemini API credentials configured

## 🔧 **Available Scripts**

### 1. **`check_croatian_translations.py`** - Analysis Script
- Analyzes current translation status
- Shows statistics about translated vs untranslated nodes
- Displays sample translations
- **Always run this first!**

### 2. **`batch_translate_croatian.py`** - Main Translation Script
- Processes Croatian nodes in batches
- Generates translations using AI
- Updates the graph with new translations
- Saves progress automatically

## 📖 **Step-by-Step Usage**

### **Step 1: Check Current Status**
Always start by analyzing the current state of your Croatian translations:

```bash
venv\Scripts\Activate.ps1; python check_croatian_translations.py
```

**Expected Output:**
```
🔍 Analyzing Croatian Graph Translation Status
==================================================
✅ Gemini API is available
📊 Croatian Graph Statistics:
   Total nodes: 29294
   Nodes with translations: 54 (0.2%)
   Nodes without translations: 29240 (99.8%)
```

### **Step 2: Test with a Small Batch (Recommended First Step)**

Before processing thousands of nodes, always test with a small batch:

```bash
# Test with 10 nodes (dry run - no changes made)
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 10 --max-batches 1 --dry-run
```

**Expected Output:**
```
🔄 DRY RUN MODE - No changes will be saved
🔍 Batch 1/1: Processing 10 nodes...
✅ Generated 7 translations (100% success rate)
💾 Would save 7 translations to graph (DRY RUN)
```

### **Step 3: Process Small Real Batches**

Once testing works, start with small real batches:

```bash
# Process 10 nodes for real
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 10 --max-batches 1

# Process 50 nodes
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 50 --max-batches 1
```

### **Step 4: Scale Up Gradually**

Once you're confident, scale up:

```bash
# Process 100 nodes in single batch
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 100 --max-batches 1

# Process 500 nodes in 5 batches of 100
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 100 --max-batches 5

# Process 1000 nodes in 10 batches of 100
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 100 --max-batches 10
```

### **Step 5: Large Scale Processing**

For processing thousands of nodes:

```bash
# Process 5000 nodes in 50 batches of 100
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 100 --max-batches 50

# Process 10000 nodes in 100 batches of 100
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 100 --max-batches 100
```

## 🔧 **Available Parameters**

### **batch_translate_croatian.py Parameters:**

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `--batch-size` | Number of nodes per batch | 100 | `--batch-size 50` |
| `--max-batches` | Maximum number of batches to process | 10 | `--max-batches 5` |
| `--dry-run` | Test mode - no changes saved | False | `--dry-run` |
| `--delay` | Delay between batches (seconds) | 1 | `--delay 2` |
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO | `--log-level DEBUG` |

### **Common Usage Patterns:**

```bash
# Quick test (10 nodes, dry run)
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 10 --max-batches 1 --dry-run

# Small real batch (25 nodes)
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 25 --max-batches 1

# Medium batch (500 nodes)
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 100 --max-batches 5

# Large batch (2000 nodes with 2-second delay)
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 100 --max-batches 20 --delay 2

# Debug mode (detailed logging)
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 50 --max-batches 2 --log-level DEBUG
```

## 📊 **Monitoring Progress**

### **During Processing:**
The script provides real-time feedback:
```
🔍 Batch 1/5: Processing 100 nodes...
✅ Generated 87 translations (87% success rate)
💾 Updated 87 nodes in graph
⏰ Batch completed in 45.2 seconds
```

### **After Processing:**
Check the results:
```bash
venv\Scripts\Activate.ps1; python check_croatian_translations.py
```

## ⚠️ **Important Considerations**

### **API Rate Limits:**
- The script includes automatic delays between API calls
- If you hit rate limits, increase the `--delay` parameter
- Start with small batches to test your API limits

### **Network Issues:**
- The script has built-in retry logic
- Failed translations are logged but don't stop the process
- You can re-run the script - it will skip already translated nodes

### **Progress Tracking:**
- The graph is saved after each batch
- If the script is interrupted, progress is preserved
- You can safely restart the script

## 🎯 **Best Practices**

### **1. Always Test First**
```bash
# Always start with a dry run
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 10 --max-batches 1 --dry-run
```

### **2. Start Small**
```bash
# Begin with small real batches
venv\Scripts\Activate.ps1; python batch_translate_croatian.py --batch-size 10 --max-batches 1
```

### **3. Monitor Progress**
```bash
# Check results regularly
venv\Scripts\Activate.ps1; python check_croatian_translations.py
```

### **4. Use Appropriate Batch Sizes**
- **Testing**: 10-25 nodes
- **Small runs**: 50-100 nodes  
- **Production**: 100 nodes per batch
- **Large scale**: 100 nodes × many batches

### **5. Handle Interruptions**
- Scripts can be safely interrupted with Ctrl+C
- Progress is automatically saved
- Re-running skips already translated nodes

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **"No module named 'flask'"**
   ```bash
   # Make sure virtual environment is activated
   venv\Scripts\Activate.ps1
   ```

2. **"SPARQLWrapper not found"**
   ```bash
   # Install missing dependencies
   venv\Scripts\Activate.ps1; pip install -r requirements.txt
   ```

3. **"API key not found"**
   - Check your Gemini API key configuration
   - Ensure the API key is valid and has sufficient quota

4. **"Connection reset"**
   - Increase delay between batches: `--delay 2`
   - Reduce batch size: `--batch-size 50`

### **Getting Help:**
- Use `--log-level DEBUG` for detailed logs
- Check the console output for specific error messages
- The script provides helpful error messages and suggestions

## 📈 **Expected Performance**

### **Translation Success Rates:**
- **Typical**: 85-95% success rate
- **Common failures**: Very short words, proper nouns, technical terms
- **Failed translations**: Logged but don't stop processing

### **Processing Speed:**
- **Small batches (10-25)**: 1-2 minutes
- **Medium batches (50-100)**: 3-5 minutes  
- **Large batches (100+)**: 5-10 minutes per batch

### **API Usage:**
- **Approximately**: 1 API call per untranslated node
- **Cost**: Varies by API provider and usage tier
- **Optimization**: Built-in caching reduces redundant calls

## 🎉 **Example Complete Workflow**

```bash
# 1. Activate virtual environment
venv\Scripts\Activate.ps1

# 2. Check current status
python check_croatian_translations.py

# 3. Test with dry run
python batch_translate_croatian.py --batch-size 10 --max-batches 1 --dry-run

# 4. Process small real batch
python batch_translate_croatian.py --batch-size 25 --max-batches 1

# 5. Check results
python check_croatian_translations.py

# 6. Scale up gradually
python batch_translate_croatian.py --batch-size 100 --max-batches 5

# 7. Monitor final results
python check_croatian_translations.py
```

## 🏁 **Success Indicators**

You'll know the process is working when you see:
- ✅ Increasing number of translated nodes
- 📈 High success rates (85%+)
- 💾 Automatic graph saving
- 🔄 Consistent batch processing
- 📊 Updated statistics in check script

---

**Created**: 2024-01-XX  
**Last Updated**: 2024-01-XX  
**Version**: 1.0

For technical support or questions, refer to the script documentation or check the logs for detailed error messages. 