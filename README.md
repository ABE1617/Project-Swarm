# 🐝 Swarm – My Local, Scalable Automation Engine

Welcome to **Swarm**, a project I built from the ground up as a fully local, modular automation engine using **Python**, **Flask**, **HTML/CSS/JS**, and **Bootstrap**. I was inspired by tools like [n8n](https://n8n.io), but I wanted more control, better local performance, and easier extensibility so I made my own XD

---

## 👋 What I Built

I designed Swarm as a **node-based visual automation builder** just like n8n but made it more developer friendly and user friendly (somehow), easier to extend, and focused entirely on **local execution**.

I implemented:

- 🧠 A fully working **Execution Engine** in Python to parse and run workflows
- ⚙️ A **modular Control Node system**, where each node is a Python file
- 🧩 A web-based **drag-and-drop GUI**, mimicking the look and flow of n8n
- 🧾 A JSON-based backend to save and run workflows
- 🔑 API-configurable nodes for OpenAI, DeepSeek, Gmail, Google Sheets, Drive, etc.

---

## 🚀 Core Features I Added

- ✅ Visual Workflow Builder (n8n-style canvas)
- ✅ Modular Node System (`/Control Nodes/` folder)
- ✅ Backend Worker Engine that processes JSON workflows
- ✅ HTTP, HTTPS, Gmail, Google Sheets, and Drive integration
- ✅ API Key authentication for third-party services
- ✅ OpenAI & DeepSeek Node support
- ✅ File Writer Node (Write to local disk)
- ✅ JSON-based workflow storage and portability
- ✅ Scalable architecture (easy to add new nodes)

---

## 🧩 Nodes I Implemented (v1.0)

| Node                 | Description                                  |
|----------------------|----------------------------------------------|
| HttpRequestNode      | Send GET/POST requests                       |
| GmailSendNode        | Send emails using Gmail                      |
| GoogleSheetsWriter   | Write rows to Google Sheets                  |
| GoogleDriveUpload    | Upload files to Google Drive                 |
| OpenAINode           | Use OpenAI API                               |
| DeepSeekNode         | Talk to DeepSeek API                         |
| WriteToFileNode      | Write data to a text file                    |
| LoggerNode           | Output logs to console or file               |
| JsonParserNode       | Parse JSON strings                           |


---

## 🤖 Why I Built This Instead of Using n8n

| Feature                    | n8n              | Swarm (My Version)           |
|---------------------------|------------------|------------------------------|
| Fully Local               | ❌               | ✅ (My top priority)         |
| Easily Add Python Nodes   | ❌ (TS-based)     | ✅ (Just add a `.py` file)   |
| Frontend Simplicity       | ✅               | ✅ (Same look, simpler code) |
| Backend Complexity        | 😵 (Heavy stack) | 😌 (Light Flask app I wrote) |
| Custom Execution Engine   | ❌               | ✅ (Written by me)           |
| IoT & File Support        | Limited          | Built-in                    |

I wanted something light, personal, extensible, and fast. Swarm is exactly that.

---

## 🔮 My Vision for Swarm
I see this as more than just a personal tool. I want Swarm to be:

### 💻 The go-to local-first automation platform

### 🔌 A sandbox for rapidly testing new APIs and data flows

### 🤖 A backend engine for IoT devices, desktops, or automation agents

### 👩‍🔧 A tool developers can modify without touching dozens of files

