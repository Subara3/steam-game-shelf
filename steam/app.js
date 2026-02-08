function dashboard() {
  return {
    games: [],
    articles: [],
    lastUpdate: '',
    error: '',
    lang: localStorage.getItem('lang') || 'ja',
    i18nData: window.__i18n || {},
    reviewScoreJa: (window.__i18n || {}).reviewScoreJa || {},

    searchQuery: '',
    selectedGenres: [],
    saleFilter: 'off',
    showOnlyWithArticle: false,
    hideR18: false,
    sortKey: 'name',
    confirmedAgeApps: {},

    t(key) {
      return (this.i18nData[this.lang] || this.i18nData.ja || {})[key] || key;
    },

    switchLang(l) {
      this.lang = l;
      localStorage.setItem('lang', l);
      this.selectedGenres = [];
    },

    gameName(g) {
      return (this.lang === 'en' ? g.name_en : g.name_ja) || g.name || '';
    },

    gameDesc(g) {
      return (this.lang === 'en' ? g.short_description_en : g.short_description_ja) || g.short_description || '';
    },

    gameRelease(g) {
      return (this.lang === 'en' ? g.release_date_en : g.release_date_ja) || g.release_date || '';
    },

    gameGenres(g) {
      return (this.lang === 'en' ? g.genres_en : g.genres_ja) || g.genres || [];
    },

    isR18(g) {
      return (g.required_age || 0) >= 18;
    },

    isAgeConfirmed(g) {
      return !!this.confirmedAgeApps[g.appid];
    },

    confirmAge(appid) {
      this.confirmedAgeApps[appid] = true;
    },

    reviewText(g) {
      const desc = g.review_score_desc || '';
      if (!desc) return '';
      if (this.lang === 'ja') {
        return this.reviewScoreJa[desc] || desc;
      }
      return desc;
    },

    get onSaleGames() {
      return this.games.filter(g => g.discount_percent > 0 && !g.coming_soon);
    },

    get comingSoonGames() {
      return this.games.filter(g => g.coming_soon);
    },

    get siteArticles() {
      return this.articles.filter(a => !a.appid);
    },

    get allGenres() {
      const counts = {};
      this.games.filter(g => !g.coming_soon).forEach(g => {
        this.gameGenres(g).forEach(genre => {
          counts[genre] = (counts[genre] || 0) + 1;
        });
      });
      return Object.entries(counts)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count);
    },

    get isFiltering() {
      return this.searchQuery || this.selectedGenres.length > 0
        || this.saleFilter !== 'off' || this.showOnlyWithArticle || this.hideR18;
    },

    get filteredGames() {
      let result = this.games.filter(g => !g.coming_soon);

      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        result = result.filter(g =>
          (g.name_en || g.name || '').toLowerCase().includes(q) ||
          (g.name_ja || '').toLowerCase().includes(q) ||
          (g.short_description || '').toLowerCase().includes(q)
        );
      }

      if (this.selectedGenres.length > 0) {
        result = result.filter(g => {
          const genres = this.gameGenres(g);
          return genres.length > 0 && this.selectedGenres.some(genre => genres.includes(genre));
        });
      }

      if (this.saleFilter !== 'off') {
        const minDiscount = { all: 1, sale50: 50, sale30: 30, sale10: 10 }[this.saleFilter] || 1;
        result = result.filter(g => (g.discount_percent || 0) >= minDiscount);
      }

      if (this.showOnlyWithArticle) {
        result = result.filter(g => g.has_article);
      }

      if (this.hideR18) {
        result = result.filter(g => !this.isR18(g));
      }

      result = [...result].sort((a, b) => {
        switch (this.sortKey) {
          case 'name':
            return (this.gameName(a)).localeCompare(this.gameName(b));
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
      this.saleFilter = 'off';
      this.showOnlyWithArticle = false;
      this.hideR18 = false;
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
        // Alpine動的テンプレート内の広告をpush
        this.$nextTick(() => {
          document.querySelectorAll('.ad-slot-inline .adsbygoogle').forEach(ins => {
            if (!ins.dataset.adsbygooglePushed) {
              try {
                (window.adsbygoogle = window.adsbygoogle || []).push({});
                ins.dataset.adsbygooglePushed = '1';
              } catch (e) { /* ignore */ }
            }
          });
        });
      } catch (e) {
        this.error = 'データの読み込みに失敗しました';
        console.error(e);
      }
    },
  };
}
