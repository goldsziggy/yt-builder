# Quotes Directory

This directory contains quote files that will be displayed during your videos.

## Usage Options

### Option 1: Single Quote Per File (Simple)
Create `.txt` files with one quote each (no special formatting needed):

```
quotes/
  ├── motivational.txt  → "Your first quote"
  ├── inspirational.txt → "Your second quote"
  └── wisdom.txt        → "Your third quote"
```

**Example file content** (`motivational.txt`):
```
The best time to plant a tree was 20 years ago. The second best time is now.
```

### Option 2: Multiple Quotes in Any File ⭐ NEW!
**Any `.txt` file** can now contain multiple quotes! Just enclose each quote in double quotes:

```
quotes/
  ├── motivational.txt  → 5 quotes about motivation
  ├── funny.txt         → 3 funny quotes
  └── wisdom.txt        → 10 quotes about wisdom
```

**Important Rules for Multiple Quotes:**
- Each quote MUST be enclosed in double quotes `"`
- Quotes can span multiple lines
- Empty lines between quotes are ignored
- To include a literal quote mark, escape it: `\"`
- Works with **ANY filename** - not just `quotes_all.txt`!

**Example `motivational.txt` with multiple quotes:**
```
"The best time to plant a tree was 20 years ago. The second best time is now."

"Success is not final, failure is not fatal: it is the courage to continue that counts."

"The only way to do great work is to love what you do."

"She said, \"Hello world!\" and smiled."
```

### Option 3: Mix Both Styles!
You can mix single and multiple quote files freely:

```
quotes/
  ├── single_quote.txt     → One quote (no quotes needed)
  ├── multiple_quotes.txt  → 5 quotes (each in "quotes")
  └── more_quotes.txt      → 3 quotes (each in "quotes")
```

## Features

- **Auto-ignore example files**: Files with 'example' in the name are automatically skipped
- **Shuffle support**: Enable shuffle in settings to randomize quote order
- **Timing control**: Configure duration and intervals in the web UI or command line

## Tips

1. Keep quotes concise (1-3 sentences work best)
2. Use clear, readable text - avoid special characters that might not render well
3. Test with a short video first to verify font and timing
4. Mix both methods: Use individual files AND quotes_all.txt - they'll all be loaded together!

## Backwards Compatibility

✅ **All existing quote files still work!**
- Old single-quote files (without double quotes) work exactly as before
- New multi-quote files (with double quotes) are automatically detected
- No changes needed to your existing setup

## How It Works

The system automatically detects the format:
1. **If the file contains text in double quotes** → Extracts each quoted section as a separate quote
2. **If no double quotes found** → Treats entire file content as a single quote

## Example Files

- `quotes_all.txt.example` - Example of multiple quotes in one file
- `motivational.txt.example` - Example showing both single and multi-quote formats work

**To use examples:** Remove the `.example` extension from any example file
