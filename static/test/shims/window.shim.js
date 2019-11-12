// Add properties to window object used by 'app.js' to avoid test errors

window.__config = {
  'SERVER_HOSTNAME': "",
  'PREFERRED_URL_SCHEME': "",
};
window.__features = {};
window.__oauth = {
  'GITHUB_TRIGGER_CONFIG': {
    'CLIENT_ID': "",
    'GITHUB_ENDPOINT': "",
    'AUTHORIZE_ENDPOINT': "",
  },
  'GITLAB_TRIGGER_CONFIG': {
    'CLIENT_ID': "",
    'GITLAB_ENDPOINT': "",
    'AUTHORIZE_ENDPOINT': "",
  }
};
window.__endpoints = {
  "/api/v1/user/": {
    "get": {
      "operationId": "getLoggedInUser",
      "parameters": []
    },
    "x-name": "endpoints.api.user.User",
    "x-path": "/api/v1/user/",
    "x-tag": "user"
  },
};
