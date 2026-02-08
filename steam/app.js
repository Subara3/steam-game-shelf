const i18n = {
  ja: {
    siteTitle: 'すばらしきSteamゲームの本棚',
    siteDesc: 'おすすめSteamゲームのセール・価格情報をお届け。気になるゲームをウィッシュリストに入れる前にチェック！',
    lastUpdate: '最終更新',
    titles: 'タイトル',
    loading: '読み込み中...',
    onSale: 'セール中！',
    gameList: 'ゲーム一覧',
    articles: '記事',
    articlesWip: '記事は準備中です。',
    search: '検索',
    searchPlaceholder: 'ゲーム名で検索...',
    genre: 'ジャンル',
    genreAll: 'すべて',
    display: '表示',
    onlySale: 'セール中のみ',
    onlyArticle: '記事ありのみ',
    sort: '並び替え',
    sortName: 'タイトル順',
    sortPriceAsc: '価格が安い順',
    sortPriceDesc: '価格が高い順',
    sortReview: 'レビュー順',
    sortDiscount: '割引率順',
    showing: '件表示',
    clearFilter: 'フィルター解除',
    noResults: '条件に一致するゲームがありません。',
    viewOnSteam: 'Steamで見る',
    readArticle: '記事を読む',
    free: '無料',
    playDemo: 'デモあり',
    trailer: 'トレーラー',
    languages: '対応言語',
  },
  en: {
    siteTitle: 'The Wonderful Steam Game Shelf',
    siteDesc: 'Track sales and prices for our favorite Steam games. Check before you wishlist!',
    lastUpdate: 'Last updated',
    titles: 'titles',
    loading: 'Loading...',
    onSale: 'On Sale!',
    gameList: 'Game List',
    articles: 'Articles',
    articlesWip: 'Articles coming soon.',
    search: 'Search',
    searchPlaceholder: 'Search by title...',
    genre: 'Genre',
    genreAll: 'All',
    display: 'Filter',
    onlySale: 'On sale only',
    onlyArticle: 'With article only',
    sort: 'Sort',
    sortName: 'By title',
    sortPriceAsc: 'Price: low to high',
    sortPriceDesc: 'Price: high to low',
    sortReview: 'By review score',
    sortDiscount: 'By discount',
    showing: ' shown',
    clearFilter: 'Clear filters',
    noResults: 'No games match the current filters.',
    viewOnSteam: 'View on Steam',
    readArticle: 'Read article',
    free: 'Free',
    playDemo: 'Demo available',
    trailer: 'Trailer',
    languages: 'Languages',
  },
};

// Steam レビュースコア EN→JP 翻訳
const reviewScoreJa = {
  'Overwhelmingly Positive': '圧倒的に好評',
  'Very Positive': '非常に好評',
  'Positive': '好評',
  'Mostly Positive': 'やや好評',
  'Mixed': '賛否両論',
  'Mostly Negative': 'やや不評',
  'Negative': '不評',
  'Very Negative': '非常に不評',
  'Overwhelmingly Negative': '圧倒的に不評',
};

function dashboard() {
  return {
    games: [],
    articles: [],
    lastUpdate: '',
    error: '',
    lang: localStorage.getItem('lang') || 'ja',

    searchQuery: '',
    selectedGenres: [],
    showOnlySale: false,
    showOnlyWithArticle: false,
    sortKey: 'name',

    t(key) {
      return (i18n[this.lang] || i18n.ja)[key] || key;
    },

    switchLang(l) {
      this.lang = l;
      localStorage.setItem('lang', l);
    },

    // 言語に応じたフィールドを返す
    gameName(g) {
      return (this.lang === 'en' ? g.name_en : g.name_ja) || g.name || '';
    },

    gameDesc(g) {
      return (this.lang === 'en' ? g.short_description_en : g.short_description_ja) || g.short_description || '';
    },

    gameRelease(g) {
      return (this.lang === 'en' ? g.release_date_en : g.release_date_ja) || g.release_date || '';
    },

    reviewText(g) {
      const desc = g.review_score_desc || '';
      if (!desc) return '';
      if (this.lang === 'ja') {
        return reviewScoreJa[desc] || desc;
      }
      return desc;
    },

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

      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        result = result.filter(g =>
          (g.name_en || g.name || '').toLowerCase().includes(q) ||
          (g.name_ja || '').toLowerCase().includes(q) ||
          (g.short_description || '').toLowerCase().includes(q)
        );
      }

      if (this.selectedGenres.length > 0) {
        result = result.filter(g =>
          g.genres && this.selectedGenres.some(genre => g.genres.includes(genre))
        );
      }

      if (this.showOnlySale) {
        result = result.filter(g => g.discount_percent > 0);
      }

      if (this.showOnlyWithArticle) {
        result = result.filter(g => g.has_article);
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
