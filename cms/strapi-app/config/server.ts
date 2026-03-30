export default ({ env }) => ({
  host: '0.0.0.0',
  port: 1337,

  url: 'https://cms.apparelbrandingcompany.in', // ✅ FIX
  proxy: true,                                  // ✅ IMPORTANT

  app: {
    keys: env.array('APP_KEYS'),
  },

  cron: {
    enabled: !env.bool('STRAPI_DISABLE_CRON', false),
  },
});
