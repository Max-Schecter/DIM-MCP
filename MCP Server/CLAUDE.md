* See @docs/CONTRIBUTING.md for project overview and @package.json for available pnpm commands for this project.
* Important code style guidelines are in @.github/copilot-instructions.md

## Project Overview

DIM (Destiny Item Manager) is a React-based web application for managing items in the Destiny video game. It's a TypeScript project using modern web technologies including React, Redux, and CSS Modules.

## Essential Commands

Strongly prefer running these pnpm commands instead of directly executing tools like tsc, eslint, or jest.

**Development:**
- `pnpm install` - Install dependencies
- `pnpm start` - Start development server on https://localhost:8080
- `pnpm fix` - Run all code formatters and linters (ESLint, Prettier, Stylelint)
- `pnpm test` - Run all tests
- `pnpm test -- -u` - Update test snapshots
- `pnpm lint` - Run linting without fixing
- `pnpm i18n` - Update localization files after adding strings
- `pnpm typecheck` - Run the TypeScript type checker tsc on the codebase

**Build:**
- `pnpm build:beta` - Build for beta environment
- `pnpm build:release` - Build for production
- `pnpm build:dev` - Build for development

**Testing:**
- `pnpm test` - Run full test suite
- `pnpm test -- --testNamePattern="pattern"` - Run specific tests

**Running Arbitrary TypeScript Code:**
- Use `tsx` instead of `ts-node` to run TypeScript code directly. For example `npx tsx my-ts-file.ts`.

## MCP Server

**Important:** All Python dependencies for the MCP Server are installed in a virtual environment. Always activate the venv before running Python commands:

```bash
# Navigate to MCP Server directory and activate venv
cd "MCP Server"
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

**MCP Server Commands:**
- Activate venv first, then run: `python MCP_server.py`

## Architecture Overview

### Core Structure
- **src/app/** - Main application code organized by feature
- **src/data/** - Static data and configuration. This should never be edited as it comes from a separate project, d2-additional-info.
- **src/locale/** - Internationalization files
- **src/testing/** - Test utilities and setup
- **config/** - Build configuration (webpack, i18n, etc.)
- **MCP Server/** - Python MCP server with FastMCP that connects to DIM via WebSocket
