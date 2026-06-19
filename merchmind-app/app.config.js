const dotenv = require('dotenv');
const path = require('path');

const env = dotenv.config({ path: path.resolve(__dirname, '.env') }).parsed || {};

module.exports = ({ config }) => ({
  ...config,
  extra: {
    API_BASE_URL: env.API_BASE_URL || 'http://localhost:8000',
    USE_MOCK_API: env.USE_MOCK_API || 'true',
    APP_API_KEY: env.APP_API_KEY || '',
    eas: {
      projectId: config.extra?.eas?.projectId,
    },
  },
});
