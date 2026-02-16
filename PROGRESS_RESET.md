# How to Reset Progress

If you want to re-download all courses from scratch, simply delete the `progress.json` file:

```bash
rm progress.json
```

Then run the downloader again. It will create a new progress file and download all content.

## What was the bug?

The script was checking the progress.json file BEFORE checking if files actually exist on disk. This meant:

1. If you downloaded courses and then deleted the `Downloads` folder
2. But kept the `progress.json` file
3. The script would skip all "completed" lessons even though the files were gone

## How it's fixed now

The script now:
1. **First** checks if the markdown file exists on disk
2. **Then** checks the progress tracking
3. If a file is missing but marked as completed, it re-downloads it

This ensures your downloads are always complete, even if files get accidentally deleted.
