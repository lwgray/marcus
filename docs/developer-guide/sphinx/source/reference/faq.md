# S Frequently Asked Questions

## General Questions

### What is Marcus?
Marcus is like a smart teacher that helps AI workers (like Claude) work together on coding projects. It assigns tasks, tracks progress, and helps when workers get stuck.

### Is it free?
Yes! Marcus itself is completely free and open source. You just need:
- Free GitHub account (recommended)
- API key from Anthropic (costs money when you use it)

### Do I need to know coding?
Not really! You just need to:
- Create tasks (like "Build a login page")
- Run simple commands
- Edit a text file (.env)

### What can I build with it?
Anything! People use Marcus to build:
- Websites
- Mobile apps
- APIs
- Games
- Tools and scripts

## Setup Questions

### Which task board should I use?
**Use GitHub!** It's free, easy, and has the most features. Only consider others if you have specific needs.

### Can I use ChatGPT instead of Claude?
Not yet, but it's planned! Marcus currently works best with Anthropic's Claude.

### Do I need a powerful computer?
No! Marcus runs in Docker, which works on most computers. You need:
- 4GB RAM (8GB better)
- 10GB free disk space
- Internet connection

### Can I run it on a server?
Yes! Use `./start.sh remote` for server deployments. Just don't use Planka online (licensing issues).

## Usage Questions

### How do I create tasks?
**For GitHub**: Create issues in your repository
**For Linear**: Create issues in your Linear workspace
**For Planka**: Create cards in your board (local only!)

### How many workers can I have?
As many as you want! Each worker needs its own API key and costs money to run.

### Can workers talk to each other?
Not directly, but Marcus shares information between them. When Worker A creates an API, Marcus tells Worker B about it!

### How do I see what workers are doing?
Check the logs:
```bash
docker-compose logs -f pm-agent
```

Or use visualization mode:
```bash
./start.sh full
```

## Troubleshooting Questions

### Why aren't workers picking up tasks?
1. Make sure tasks exist in your board
2. Check tasks have priority labels
3. Verify workers are running (`docker-compose ps`)
4. Look for errors in logs

### Can I pause/resume work?
Yes! Just stop and start Marcus:
```bash
docker-compose down  # Stop
./start.sh          # Resume
```

### What if a worker gets stuck?
Workers will report blockers to Marcus, which uses AI to suggest solutions. Check logs to see the suggestions!

### How do I update Marcus?
```bash
git pull
docker-compose build --no-cache
./start.sh
```

## Cost Questions

### How much does it cost?
- **Marcus**: Free!
- **GitHub**: Free!
- **Anthropic API**: About $0.01-0.10 per task (depends on complexity)
- **Linear**: $8/user/month (optional)

### How can I reduce costs?
1. Use smaller, simpler tasks
2. Run fewer workers
3. Use Claude Haiku (cheaper model) when available
4. Stop Marcus when not using it

## Advanced Questions

### Can I customize worker behavior?
Yes! Edit `prompts/system_prompts.md` to change how workers act.

### Can I add my own tools?
Yes, but it requires Python knowledge. Check the Contributing Guide in the repository.

### Can Marcus work with my existing project?
Absolutely! Just point it to your GitHub repo and create issues for what needs to be done.

### Is my code private?
- Your code stays in your GitHub repo (private if you want)
- Anthropic processes requests but doesn't store your code
- Logs are stored locally in `logs/` folder

## Legal Questions

### Can I use this for commercial projects?
Yes! Marcus is MIT licensed - use it for anything!

### What about Planka licensing?
Planka uses AGPL license - only use it locally, never online. Use GitHub or Linear for commercial/online use.

### Who owns the code workers create?
You do! Workers are just tools you're using.

## Still Have Questions?

1. Check [Troubleshooting](troubleshooting.md) for technical issues
2. Read How It Works for deeper understanding
3. Ask on GitHub Issues for help

---

=� **Pro Tip**: Most questions are answered by just trying it! Run `./start.sh demo` to see Marcus in action.