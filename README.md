# 🤖 TT Quiz Bot

A Telegram-based quiz bot where admins can create tests and users can take quizzes and view leaderboards.

---

## 🚀 Features

### 👨‍💻 For Admin:

* ➕ Add new tests (`/addtest`)
* 📋 View all tests (`/listtests`)
* 🗑 Delete tests (`/deletetest`)

### 👤 For Users:

* 🎯 Take quizzes (`/takequiz`)
* 📊 View leaderboard (`/leaderboard`)

---

## 🛠 Tech Stack

* Python
* python-telegram-bot
* PostgreSQL
* SQLAlchemy

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/tt-quiz-bot.git
cd tt-quiz-bot
```

### 2. Create virtual environment

```bash
python -m venv venv
```

### 3. Activate environment

**Windows:**

```bash
venv\Scripts\activate
```

**Linux / Mac:**

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Configuration

Create a `config.py` file:

```python
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789
DATABASE_URL = "postgresql://user:password@localhost/dbname"
```

---

## ▶️ Run the Bot

```bash
python bot.py
```

---

## 🧠 Test Input Format

When adding a test, use this format:

```
1. Question text?
*Correct answer
Wrong answer
Wrong answer

2. Another question?
*Correct answer
Wrong answer
```

---

## 🗂 Project Structure

```
├── bot.py
├── db_manager.py
├── parser.py
├── config.py
├── requirements.txt
└── README.md
```

---

## 📊 How It Works

1. Admin creates a test
2. Questions are stored in the database
3. User takes the quiz
4. Results are saved
5. Leaderboard is generated

---

## 🧩 Key Features

* Randomized questions and answers
* Global and monthly leaderboard
* Inline keyboard navigation
* PostgreSQL database support

---

## ⚠️ Notes

* Telegram user IDs can be large → `BigInteger` is used in DB
* Callback data must not exceed 64 characters

---

## 👨‍💻 Author

Abduvohid

---

## ⭐ Support

If you like this project, don’t forget to give it a ⭐ on GitHub!
