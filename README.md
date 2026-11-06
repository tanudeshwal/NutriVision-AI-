# NutriVision AI – AI Food Analyzer

## Features
- Food image upload and Food-101 image classification
- Approximate nutrition lookup for included Indian and international foods
- Educational nutrition heuristic
- Optional MongoDB registration, login and food history
- Responsive Bootstrap interface

## Requirements
- Python 3.10 or 3.11 recommended
- Internet connection for the first model download
- MongoDB Atlas or local MongoDB for accounts/history (optional for image analysis)

## Windows setup (VS Code / PowerShell)
1. Extract this ZIP.
2. Open the `ai_food_analyzer` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\venv\Scripts\Activate.ps1
   ```

5. Install packages:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

   PyTorch installation can vary by computer. If `pip install -r requirements.txt` fails on `torch`, install PyTorch using the official selector at https://pytorch.org/get-started/locally/ and then run `pip install -r requirements.txt` again.

6. Copy `.env.example` to `.env`. Set a long random `SECRET_KEY`. For accounts and history, add your MongoDB connection string as `MONGO_URI`. Without MongoDB, image analysis still works but registration/history will not.
7. Start the website:

   ```powershell
   python app.py
   ```

8. Open http://127.0.0.1:5000

The first analysis downloads the selected model and can take several minutes. Keep the terminal running.

## Model scope and limitations
The default `nateraw/food` model is a Food-101 classifier. It predicts one main dish per image; it is not a multi-object detector and does not guarantee reliable recognition of every Indian dish. For a college-grade expanded model, collect a balanced Indian + international food dataset, fine-tune a classifier, and evaluate it on held-out images. For multiple foods in one plate, train/use an object detector and estimate each item's portion separately.

Nutrition values in `nutrition.py` are approximate reference-serving examples. They are not calculated from pixels or exact portion size. Add verified values from a trusted nutrition source (such as USDA FoodData Central) and cite the source in your report. Do not use the heuristic score as medical advice.

## Suggested next development milestones
1. Add serving-size controls and scale all nutrients proportionally.
2. Add a verified nutrition API and caching.
3. Train and evaluate an Indian-food classifier.
4. Add object detection for multi-item plates.
5. Add charts for daily calories/macros and secure production deployment.
6. Add CSRF protection, rate limiting, upload validation, and production secret management before public deployment.
