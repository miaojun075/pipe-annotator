# Contributing to PipeAnnotator

Thanks for your interest in contributing! PipeAnnotator is an industrial computer vision tool for pipe fitting recognition, built with Python + OpenCV + PyTorch.

## How to Help

### 🐛 Bug Reports
- Search [existing issues](../../issues) first
- Include: your OS, Python version, error traceback, and a sample image if possible
- Use the bug report template

### 💡 Feature Requests
- Explain the problem you're trying to solve, not just the solution
- Industrial pipe fitting domain knowledge is highly valued — share your use case

### 🔧 Code Contributions

1. **Fork** the repo
2. **Create a branch**: `feature/your-feature` or `fix/your-fix`
3. **Keep PRs focused**: one feature/fix per PR
4. **Test your changes**: run the pipeline on at least 3 sample images
5. **Follow existing style**: the project uses plain Python with type hints where practical

### 🏗️ Project Architecture

```
Image → FastSAM Segmentation → GridRescue → HSV Filter → 
CNN KNN Classification → DN Area Lookup → NCC Fine-match → SKU Output
```

Key modules:
- `gui.py` — Tkinter desktop UI + detection pipeline orchestration
- `fastsam_segmenter.py` — FastSAM-based pipe fitting segmentation
- `cnn_classifier.py` — MobileNetV2 feature extraction + KNN classification
- `fitting_matcher.py` — NCC template matching for fine-grained matching
- `yolo_exporter.py` — YOLO training data export (bbox + segment)
- `camera.py` — Camera capture + Otsu segmentation fallback

### 📦 Development Setup

```bash
# Create virtualenv
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Download base models (see README for links)
# - FastSAM-x.pt → project root
# - yolo11n.pt → project root

# Run
python main.py
```

### 🎯 Prioritized Needs

1. **Improve steel fitting detection** — dark steel fittings on gray steel tables have low contrast; better segmentation needed
2. **YOLO training pipeline** — clean up training data noise, optimize for small objects (25-100px)
3. **Cross-platform support** — macOS/Linux compatibility
4. **Performance optimization** — batch inference, GPU support
5. **Test coverage** — unit tests for core pipeline modules

### 📝 Code Style

- Python 3.10+
- UTF-8 encoding (Chinese comments OK)
- Type hints encouraged but not mandatory
- Docstrings for public methods

### ⚠️ What NOT to Contribute

- The gallery database (gallery_v2) is proprietary — do not submit trained model weights or feature databases
- Training data containing personal/third-party images without consent

---

Questions? Open a discussion or email the maintainer.
