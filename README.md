# MetaNotes

Keep notes and metadata for your files **without touching the files themselves**. Perfect for artists, developers, data scientists, or anyone who wants a **centralized, portable annotation system**.

## 🧐 What is a MetaNote?

A **MetaNote** is a piece of information you want to store about a file or folder, **alongside your data but without modifying it**.

### Examples:

* You downloaded a 3D asset and want to keep the **original source link**.
* Track **licenses or credits** for images, sounds, or other assets.
* Write **reminders, explanations, or notes** on datasets.
* Keep track of **how or why you organized your project**.

**How it works:**

1. Open a directory in MetaNotes (e.g., `Assets/`).
2. The sidebar displays all **files and subfolders**.
3. Open a **note for each item** in tabs.
4. All notes are stored in a single hidden file: **`.metanotes.json`** in the folder.

> ⚡ `.metanotes.json` contains all MetaNotes for **files and subfolders** in that directory. No clutter, no duplicate note files — just one centralized, portable JSON.


## 🚀 Features

* Notes for **any file or folder**.
* Centralized storage with **one `.metanotes.json` per folder**.
* Simple, fast, and **non-intrusive** — your original files remain untouched.
* Tabs for **quick navigation between notes**.
* Portable — move or share your folder along with `.metanotes.json`.


## 💾 Installation

**Option 1: Download prebuilt binaries**

* Go to the [Releases](#) page and download for your OS.
* Unzip and run the app.

**Option 2: Build from source**

```bash
git clone https://github.com/yourusername/metanotes.git
cd metanotes
# Follow build instructions for your OS
```


## 🛠 Usage

1. Open MetaNotes and select a **folder**.
2. Click a file or subfolder in the sidebar.
3. Write or edit your MetaNote in the tab that opens.
4. All notes are **automatically saved** in `.metanotes.json`.

> Notes are **instantaneously attached to the folder contents**, and the file remains hidden to keep your workspace clean.


## ❓ FAQ

**Q: Can I edit `.metanotes.json` manually?**
A: Yes, it’s a plain JSON file. But using MetaNotes ensures proper formatting.

**Q: Will MetaNotes change my files?**
A: Never. MetaNotes **store data externally** in `.metanotes.json`.

**Q: Can I track notes across nested folders?**
A: Each folder has its **own `.metanotes.json`**, so notes stay local but portable.


## 📂 Example

```
Assets/
├─ character.obj
├─ environment.fbx
├─ texture.png
└─ .metanotes.json   ← contains notes for all items in this folder
```