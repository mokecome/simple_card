const { createProxyMiddleware } = require('http-proxy-middleware');

const proxy = createProxyMiddleware({
  target: 'http://localhost:8006',
  changeOrigin: true,
  autoRewrite: true,
  protocolRewrite: 'https',
});

module.exports = function (app) {
  // /spider (exact, no trailing slash) → let React Router handle it
  app.use('/spider', (req, res, next) => {
    if (req.path === '/' && req.originalUrl === '/spider') {
      return next('route');
    }
    return proxy(req, res, next);
  });

  // Avoid /static/js, /static/css which belong to React dev server
  ['/api', '/health', '/config', '/static/card_data', '/static/uploads']
    .forEach(path => app.use(path, proxy));
};
