/**
 * api.js – PatTat · Multiplayer Edition
 */
const API = {
  async get(url)           { return (await fetch(url)).json(); },
  async post(url, data={}) {
    return (await fetch(url, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
    })).json();
  },

  // Auth
  ich()                   { return this.get('/api/ich'); },
  getUser()               { return this.get('/api/user/ich'); },
  login(name, passwort)   { return this.post('/api/login',    {name, passwort}); },
  register(name, passwort){ return this.post('/api/register', {name, passwort}); },
  logout()                { return this.post('/api/logout'); },

  // Heartbeat & Online
  heartbeat()             { return this.post('/api/heartbeat'); },
  spielerOnline()         { return this.get('/api/spieler/online'); },

  // Benachrichtigungen
  benachrichtigungen()    { return this.get('/api/benachrichtigungen'); },

  // Welt
  getTiere()                   { return this.get('/api/tiere'); },
  getTier(id)                  { return this.get(`/api/tier/${id}`); },
  blattSammeln()               { return this.post('/api/blatt_sammeln'); },
  zaehmen(tier_id)             { return this.post('/api/zaehmen',  {tier_id}); },
  neuesWildtier(art, rang)     { return this.post('/api/wildtier', {art, rang}); },
  zuechten(vater_id, mutter_id){ return this.post('/api/zuechten', {vater_id, mutter_id}); },

  // Markt
  getMarkt()                        { return this.get('/api/markt'); },
  marktEinstellen(tier_id, preis)   { return this.post('/api/markt/einstellen',   {tier_id, preis}); },
  marktKaufen(tier_id)              { return this.post('/api/markt/kaufen',        {tier_id}); },
  marktZurueckziehen(tier_id)       { return this.post('/api/markt/zurueckziehen', {tier_id}); },

  // Verhandlung
  verhandlungStarten(tier_id)              { return this.post('/api/verhandlung/starten',   {tier_id}); },
  verhandlungAngebot(tier_id, gebot)       { return this.post('/api/verhandlung/angebot',   {tier_id, gebot}); },
  verhandlungAbschluss(tier_id, endpreis)  { return this.post('/api/verhandlung/abschluss', {tier_id, endpreis}); },

  // Einstellungen
  einstellungenLesen()        { return this.get('/api/user/einstellungen'); },
  einstellungenSpeichern(data){ return this.post('/api/user/einstellungen', data); },

  // Trades
  tradesHolen()           { return this.get('/api/trades/meine'); },
  tradeAnbieten(an, wuensche_tier_id, biete_tier_id, gebot_coins=0) {
    return this.post('/api/trade/anbieten', {an, wuensche_tier_id, biete_tier_id, gebot_coins});
  },
  tradeAnnehmen(trade_id) { return this.post(`/api/trade/annehmen/${trade_id}`); },
  tradeAblehnen(trade_id) { return this.post(`/api/trade/ablehnen/${trade_id}`); },

  // Stammbaum
  getStammbaum(id)        { return this.get(`/api/stammbaum/${id}`); },

  // Chat & Nachrichten
  nachrichtSenden(an, text){ return this.post('/api/nachricht/senden', {an, text}); },
  postfach()               { return this.get('/api/nachrichten/postfach'); },
  verlauf(partner)         { return this.get(`/api/nachrichten/verlauf/${encodeURIComponent(partner)}`); },
  ungeleseneAnzahl()       { return this.get('/api/nachrichten/ungelesen_anzahl'); },

  // Soziales (Freunde + Blockieren)
  sozialdaten()            { return this.get('/api/sozialdaten'); },
  freundHinzufuegen(name)  { return this.post('/api/freunde/hinzufuegen', {name}); },
  freundEntfernen(name)    { return this.post('/api/freunde/entfernen',   {name}); },
  blockieren(name)         { return this.post('/api/blockieren',          {name}); },
  entblockieren(name)      { return this.post('/api/entblockieren',       {name}); },
};
