# 📜 PM Agent Licensing Guide

## PM Agent License
PM Agent itself is licensed under the MIT License - you can use it freely for any purpose, including commercial use.

## Kanban Provider Licensing

PM Agent supports multiple kanban providers with different licenses:

### ✅ GitHub Issues
- **License**: GitHub's Terms of Service
- **Commercial Use**: ✅ Yes
- **Remote Hosting**: ✅ Yes
- **Restrictions**: None for PM Agent usage
- **Best For**: Open source projects, commercial projects, remote deployments

### ✅ Linear
- **License**: Linear's Terms of Service
- **Commercial Use**: ✅ Yes (with paid plan)
- **Remote Hosting**: ✅ Yes
- **Restrictions**: API rate limits
- **Best For**: Professional teams, commercial projects

### ⚠️ Planka
- **License**: AGPL-3.0 (Affero General Public License)
- **Commercial Use**: ⚠️ Complex - requires compliance with AGPL
- **Remote Hosting**: ❌ Not recommended
- **Restrictions**: Must share source code of entire application if publicly hosted
- **Best For**: Personal use, local development, internal tools

## Important: Planka AGPL Implications

If you use Planka with PM Agent:

1. **Local Use Only**: We strongly recommend using Planka ONLY for local deployments
2. **No Public Hosting**: Do NOT host Planka publicly without understanding AGPL requirements
3. **Source Code Sharing**: AGPL requires you to share the source code of your ENTIRE application (including PM Agent modifications) if you offer it as a network service
4. **Alternative Options**: Use GitHub or Linear for any remote/commercial deployments

## Deployment Recommendations

### For Remote/Public Hosting
```bash
# Use GitHub (recommended)
KANBAN_PROVIDER=github ./start.sh remote

# Or use Linear
KANBAN_PROVIDER=linear ./start.sh remote
```

### For Local Development
```bash
# Any provider is fine locally
./start.sh              # GitHub/Linear
./start.sh local-planka # Planka (local only)
```

## Compliance Checklist

- [ ] **Using GitHub/Linear?** You're good to go! 
- [ ] **Using Planka locally?** That's fine for personal use
- [ ] **Want to host Planka publicly?** ❌ We don't recommend this
- [ ] **Need remote access?** Use GitHub or Linear instead

## Why We Made This Choice

1. **Flexibility**: Users can choose the best provider for their needs
2. **Safety**: Default configurations are license-compliant
3. **Clarity**: Clear warnings prevent accidental AGPL violations
4. **Options**: Commercial users have GitHub/Linear, hobbyists can use Planka locally

## Questions?

- **"Can I use PM Agent commercially?"** Yes! PM Agent is MIT licensed
- **"Can I host PM Agent with GitHub/Linear?"** Yes, absolutely!
- **"Can I host PM Agent with Planka?"** Technically yes, but we strongly discourage it due to AGPL
- **"What if I need Planka features?"** Use it locally, or consider switching to GitHub Projects

Remember: When in doubt, use GitHub Issues - it's free, powerful, and has no licensing concerns!