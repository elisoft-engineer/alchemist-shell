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

- **Smart Proxying**  
  Call `db.commit()`, `db.add()`, and `db.rollback()` as sync methods. Async is handled under the hood.

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

### 1. Zero-Await Session Management

Interact with your session without the async tax:

```python
alchemist ❯ user = User(username="alchemist")
alchemist ❯ db.add(user)
alchemist ❯ db.commit()
```

---

### 2. Immediate Feedback

Stop calling `print()` or `vars()`. Just evaluate the variable:

```python
alchemist ❯ user
# Renders a clean table with all column values
```

---

### 3. Native Async Queries

Full auto-await support when you need complex queries:

```python
alchemist ❯ orders = (await db.execute(select(Order))).scalars().all()
```

---

## 📜 License

MIT License. Permissive and simple.

---

**Built to make SQLAlchemy development suck less.**