const path = require('path');
const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');

/**
 * Metro configuration. The app source lives one level up in tv/src (the
 * contract puts tv/src/config.ts there), so Metro must watch that folder and
 * resolve its imports from this project's node_modules.
 * https://reactnative.dev/docs/metro
 *
 * @type {import('@react-native/metro-config').MetroConfig}
 */
const config = {
  watchFolders: [path.resolve(__dirname, '../src')],
  resolver: {
    nodeModulesPaths: [path.resolve(__dirname, 'node_modules')],
  },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
