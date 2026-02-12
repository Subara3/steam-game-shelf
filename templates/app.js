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
    sortKey: 'name',
    confirmedAgeApps: {},
    sidebarOpen: false,
    currentPage: 1,
    pageSize: 12,

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
      const tags = this.lang === 'en' ? g.tags_en : g.tags_ja;
      if (tags && tags.length > 0) return tags;
      return (this.lang === 'en' ? g.genres_en : g.genres_ja) || g.genres || [];
    },

    gameMainGenres(g) {
      const genres = (this.lang === 'en' ? g.genres_en : g.genres_ja) || g.genres || [];
      if (genres.length > 0) return genres;
      const tags = this.lang === 'en' ? g.tags_en : g.tags_ja;
      return (tags || []).slice(0, 3);
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

    get freeGames() {
      return this.games.filter(g => g.free_section);
    },

    get siteArticles() {
      return this.articles.filter(a => !a.appid && a.lang === this.lang);
    },

    articleUrl(slug) {
      return this.lang === 'en' ? `articles/en/${slug}.html` : `articles/${slug}.html`;
    },

    gameHasArticle(g) {
      return this.lang === 'en' ? g.has_article_en : g.has_article;
    },

    get allMainGenres() {
      const excluded = this.lang === 'en'
        ? ['Indie', 'Early Access']
        : ['インディー', '早期アクセス'];
      const counts = {};
      this.games.filter(g => !g.coming_soon && !g.free_section).forEach(g => {
        const genres = (this.lang === 'en' ? g.genres_en : g.genres_ja) || g.genres || [];
        genres.forEach(genre => {
          if (!excluded.includes(genre)) counts[genre] = (counts[genre] || 0) + 1;
        });
      });
      return Object.entries(counts)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count);
    },

    get allTags() {
      const genreNames = new Set(this.allMainGenres.map(g => g.name));
      const excluded = this.lang === 'en'
        ? ['Singleplayer', 'Multiplayer', 'Indie', 'Early Access', 'Replay Value', 'Moddable']
        : ['シングルプレイヤー', 'マルチプレイヤー', 'インディー', '早期アクセス', 'リプレイ性', 'MOD導入可能'];
      const counts = {};
      this.games.filter(g => !g.coming_soon && !g.free_section).forEach(g => {
        const tags = (this.lang === 'en' ? g.tags_en : g.tags_ja) || [];
        tags.forEach(tag => {
          if (!excluded.includes(tag) && !genreNames.has(tag)) {
            counts[tag] = (counts[tag] || 0) + 1;
          }
        });
      });
      return Object.entries(counts)
        .filter(([_, count]) => count >= 3)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count);
    },

    get isFiltering() {
      return this.searchQuery || this.selectedGenres.length > 0
        || this.saleFilter !== 'off' || this.showOnlyWithArticle;
    },

    get filteredGames() {
      let result = this.games.filter(g => !g.coming_soon && !g.free_section);

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
          const genres = this.gameMainGenres(g);
          const tags = (this.lang === 'en' ? g.tags_en : g.tags_ja) || [];
          const all = [...new Set([...genres, ...tags])];
          return this.selectedGenres.some(s => all.includes(s));
        });
      }

      if (this.saleFilter !== 'off') {
        const minDiscount = { all: 1, sale50: 50, sale30: 30, sale10: 10 }[this.saleFilter] || 1;
        result = result.filter(g => (g.discount_percent || 0) >= minDiscount);
      }

      if (this.showOnlyWithArticle) {
        result = result.filter(g => this.gameHasArticle(g));
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

    get totalPages() {
      return Math.max(1, Math.ceil(this.filteredGames.length / this.pageSize));
    },

    get paginatedGames() {
      const start = (this.currentPage - 1) * this.pageSize;
      return this.filteredGames.slice(start, start + this.pageSize);
    },

    get displayRange() {
      const total = this.filteredGames.length;
      if (total === 0) return '';
      const start = (this.currentPage - 1) * this.pageSize + 1;
      const end = Math.min(this.currentPage * this.pageSize, total);
      return this.t('paginationShowing')
        .replace('{total}', total)
        .replace('{start}', start)
        .replace('{end}', end);
    },

    get pageNumbers() {
      const total = this.totalPages;
      const current = this.currentPage;
      if (total <= 7) {
        return Array.from({ length: total }, (_, i) => i + 1);
      }
      const pages = [];
      pages.push(1);
      if (current > 3) pages.push('...');
      for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        pages.push(i);
      }
      if (current < total - 2) pages.push('...');
      pages.push(total);
      return pages;
    },

    goToPage(n) {
      if (n < 1 || n > this.totalPages) return;
      this.currentPage = n;
      const grid = document.querySelector('.game-list');
      if (grid) {
        grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    },

    toggleGenre(genre) {
      const idx = this.selectedGenres.indexOf(genre);
      if (idx === -1) {
        this.selectedGenres.push(genre);
      } else {
        this.selectedGenres.splice(idx, 1);
      }
      this.currentPage = 1;
    },

    clearFilters() {
      this.searchQuery = '';
      this.selectedGenres = [];
      this.saleFilter = 'off';
      this.showOnlyWithArticle = false;
      this.currentPage = 1;
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
        // フィルタ変更時にページを1にリセット
        this.$watch('searchQuery', () => { this.currentPage = 1; });
        this.$watch('saleFilter', () => { this.currentPage = 1; });
        this.$watch('showOnlyWithArticle', () => { this.currentPage = 1; });
        this.$watch('sortKey', () => { this.currentPage = 1; });

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
