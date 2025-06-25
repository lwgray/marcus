# 🏛️ Marcus - AI Project Coordination System

Think of Marcus as a smart project manager that helps AI workers build software together. It's like having a teacher who assigns homework to different students based on what they're good at!

## 🎯 What Does It Do?

Marcus helps AI workers (like Claude) work together on coding projects by:
- 📋 **Giving out tasks** - Like a teacher assigning homework
- 👀 **Watching progress** - Making sure work gets done
- 🧩 **Sharing knowledge** - Telling workers what others have built
- 🚧 **Solving problems** - Helping when workers get stuck

## 🚀 Super Quick Start (30 seconds!)

```bash
# 1. Download Marcus
git clone <this-repo>
cd pm-agent

# 2. Start it up
./start.sh

# 3. Add your API keys
nano .env  # (or open .env in any text editor)

# 4. Restart with your settings
docker-compose restart
```

That's it! Marcus is now running.

## 📚 Documentation

### For Beginners
- [**Getting Started**](docs/getting-started.md) - Your first time? Start here!
- [**How It Works**](docs/how-it-works.md) - Simple explanation of Marcus

### Setting It Up  
- [**Installation Guide**](docs/installation.md) - Detailed setup instructions
- [**Choosing Your Task Board**](docs/providers.md) - GitHub, Linear, or Planka?
- [**Configuration**](docs/configuration.md) - All the settings explained

### Using Marcus
- [**Quick Commands**](docs/commands.md) - Common commands reference
- [**Deployment Options**](docs/deployment.md) - Local vs Remote hosting
- [**Troubleshooting**](docs/troubleshooting.md) - When things go wrong

### Advanced Topics
- [**Architecture**](docs/architecture.md) - How Marcus is built
- [**API Reference**](docs/api.md) - For developers
- [**Contributing**](CONTRIBUTING.md) - Help make Marcus better!

## 🎮 Different Ways to Run

```bash
./start.sh              # Basic mode (recommended)
./start.sh demo         # See it work with fake workers
./start.sh full         # With visual dashboard
./start.sh remote       # For hosting online
```

## 📋 Task Board Options

Marcus works with different task boards (like different brands of notebooks):

| Task Board | Good For | Cost | Setup Time |
|------------|----------|------|------------|
| **GitHub** | Most people | Free | 2 minutes |
| **Linear** | Companies | Paid | 3 minutes |
| **Planka** | Home use only | Free | 5 minutes |

## ⚠️ Important Notes

- **Planka** can only be used on your own computer (not online) due to licensing rules
- **GitHub** is recommended for most users - it's free and powerful
- You need API keys (like passwords) for the AI features to work

## 🆘 Need Help?

1. Check [Troubleshooting](docs/troubleshooting.md)
2. Look at [Common Questions](docs/faq.md)
3. Open an issue on GitHub

## 📄 License

Marcus is open source (MIT License) - you can use it for anything!

---

🥔 Made with ❤️ in Boise, Idaho