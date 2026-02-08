function dashboard() {
  return {
    games: [],
    articles: [],
    lastUpdate: '',
    error: '',

    get onSaleGames() {
      return this.games.filter(g => g.discount_percent > 0);
    },

    formatYen(amount) {
      if (!amount) return '';
      // Steam API returns price in cents (e.g. 148000 = ¥1,480)
      const yen = Math.round(amount / 100);
      return `¥${yen.toLocaleString()}`;
    },

    async init() {
      try {
        const [gamesResp, articlesResp] = await Promise.all([
          fetch('data/games.json'),
          fetch('data/articles.json'),
        ]);

        if (gamesResp.ok) {
          const data = await gamesResp.json();
          this.games = data.games || [];
          this.lastUpdate = data.date || '';
        }

        if (articlesResp.ok) {
          this.articles = await articlesResp.json();
        }
      } catch (e) {
        this.error = 'データの読み込みに失敗しました';
        console.error(e);
      }
    },
  };
}
