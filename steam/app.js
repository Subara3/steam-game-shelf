function dashboard() {
  return {
    games: [],
    articles: [],
    lastUpdate: '',
    error: '',

    // フィルター状態
    searchQuery: '',
    selectedGenres: [],
    showOnlySale: false,
    showOnlyWithArticle: false,
    sortKey: 'name',

    get onSaleGames() {
      return this.games.filter(g => g.discount_percent > 0);
    },

    get allGenres() {
      const counts = {};
      this.games.forEach(g => {
        (g.genres || []).forEach(genre => {
          counts[genre] = (counts[genre] || 0) + 1;
        });
      });
      return Object.entries(counts)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count);
    },

    get filteredGames() {
      let result = this.games;

      // テキスト検索
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        result = result.filter(g =>
          g.name.toLowerCase().includes(q) ||
          (g.short_description || '').toLowerCase().includes(q)
        );
      }

      // ジャンルフィルター
      if (this.selectedGenres.length > 0) {
        result = result.filter(g =>
          g.genres && this.selectedGenres.some(genre => g.genres.includes(genre))
        );
      }

      // セール中のみ
      if (this.showOnlySale) {
        result = result.filter(g => g.discount_percent > 0);
      }

      // 記事ありのみ
      if (this.showOnlyWithArticle) {
        result = result.filter(g => g.has_article);
      }

      // ソート
      result = [...result].sort((a, b) => {
        switch (this.sortKey) {
          case 'name':
            return a.name.localeCompare(b.name);
          case 'price_asc':
            return (a.price_final || 0) - (b.price_final || 0);
          case 'price_desc':
            return (b.price_final || 0) - (a.price_final || 0);
          case 'review':
            const aRate = a.total_reviews ? a.total_positive / a.total_reviews : 0;
            const bRate = b.total_reviews ? b.total_positive / b.total_reviews : 0;
            return bRate - aRate;
          case 'discount':
            return (b.discount_percent || 0) - (a.discount_percent || 0);
          default:
            return 0;
        }
      });

      return result;
    },

    toggleGenre(genre) {
      const idx = this.selectedGenres.indexOf(genre);
      if (idx === -1) {
        this.selectedGenres.push(genre);
      } else {
        this.selectedGenres.splice(idx, 1);
      }
    },

    clearFilters() {
      this.searchQuery = '';
      this.selectedGenres = [];
      this.showOnlySale = false;
      this.showOnlyWithArticle = false;
    },

    formatYen(amount) {
      if (!amount) return '';
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
