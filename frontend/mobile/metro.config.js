// Metro config for the Karwan-e-Khizr mobile app.
//
// This project imports shared code from `../shared` (see e.g.
// src/screens/*.tsx importing `../../../shared/...`), which lives OUTSIDE
// this Expo project's root (`frontend/mobile`). Metro only watches/resolves
// files inside the project root by default, so without `watchFolders`
// pointing at the sibling `shared/` directory, those imports fail to
// resolve at bundle time even though they typecheck fine (tsconfig's
// `paths` only affects TypeScript, not Metro's runtime module resolution).

const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '..');

const config = getDefaultConfig(projectRoot);

// Let Metro see and watch the shared package.
config.watchFolders = [path.resolve(workspaceRoot, 'shared')];

// Metro resolves node_modules relative to each file it processes by
// walking up directories; make sure it still finds this project's
// node_modules when resolving files under the (sibling, outside-root)
// shared/ directory.
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
];

module.exports = config;
