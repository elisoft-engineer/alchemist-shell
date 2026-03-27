# 🔮 Alchemist Shell

**The missing interactive shell for SQLAlchemy.**

Working with SQLAlchemy in a standard REPL is painful. You have to manually manage imports, handle async event loops, and deal with unreadable object representations. **Alchemist Shell** turns your terminal into a powerful, zero-setup database workbench.

---

## 🛠 Why this exists?

The current workflow for inspecting SQLAlchemy projects in the terminal is broken:

1. **Manual Setup**  
   You shouldn't have to manually import every model and session helper just to check a record.

2. **Manual Session Management**  
   In interactive environments, setting up and managing a session is repetitive boilerplate.  
   Creating engines, instantiating sessions, and keeping them alive just to run a few queries breaks the flow.

3. **Bad Visibility**  
   Default object reprs like `<User 1>` tell you nothing. You deserve to see your data clearly.

---

## ✨ DX Features

- **Auto-Discovery**  
  Recursively scans your project and injects all models into the namespace instantly.

- **Pre-loaded Toolkit**  
  `select`, `func`, `text`, and other SQLAlchemy essentials are available on startup.

- **Auto-Formatting**  
  Model instances render as high-fidelity `rich` tables when evaluated.

- **Modern Shell**  
  Powered by IPython with completion, syntax highlighting, and history-based autosuggestions.

---

## 📦 Installation

```bash
pip install alchemist-shell
```

---

## 🧪 The Workflow

### 1. Initialize the shell

Interact with your db having to manually load your session:

```bash
alchemist shell
```

### 2. Run queries directly on the terminal

All your SQLAlchemy models are autodiscovered and imported:

```python
alchemist ❯ user = User(username="alchemist")
alchemist ❯ await db.add(user)
alchemist ❯ await db.commit()
```

---

### 2. Immediate Feedback

View your database objects as a formated table without creating a sophisticated `__repr__` method:

```python
alchemist ❯ user
# Renders a clean table with all column values
```

---

### 3. Native Async Queries

Full auto-await support when you need complex queries:

```python
alchemist ❯ results = await db.execute(select(Order))
alchemist ❯ orders = results.scalars().all()
```

---

## 📜 License

MIT License. Permissive and simple.

---

**Built to make SQLAlchemy development suck less.**