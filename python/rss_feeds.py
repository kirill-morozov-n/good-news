"""
RSS feed definitions by category.
Each entry: url + hashtags for Telegram post.
"""

RSS_FEEDS = [
    # AI / ML
    {"url": "https://venturebeat.com/category/ai/feed/", "hashtags": "#AI #нейросети"},
    {"url": "https://huggingface.co/blog/feed.xml", "hashtags": "#AI #нейросети #OpenSource"},
    {"url": "https://www.technologyreview.com/feed/", "hashtags": "#AI #технологии"},
    {"url": "https://aiweekly.co/issues.rss", "hashtags": "#AI #нейросети"},
    {"url": "https://importai.substack.com/feed", "hashtags": "#AI #нейросети"},

    # VR / XR / AR
    {"url": "https://www.roadtovr.com/feed/", "hashtags": "#VR #AR #XR"},
    {"url": "https://uploadvr.com/feed/", "hashtags": "#VR #AR #XR"},
    {"url": "https://mixed-news.com/en/feed/", "hashtags": "#VR #AR #XR"},

    # Technology
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "hashtags": "#технологии #гаджеты"},
    {"url": "https://www.theverge.com/rss/index.xml", "hashtags": "#технологии #гаджеты"},
    {"url": "https://www.wired.com/feed/rss", "hashtags": "#технологии"},
    {"url": "https://www.engadget.com/rss.xml", "hashtags": "#технологии #гаджеты"},
    {"url": "https://www.zdnet.com/news/rss.xml", "hashtags": "#технологии"},

    # Startups
    {"url": "https://techcrunch.com/category/startups/feed/", "hashtags": "#стартапы #инвестиции"},
    {"url": "https://news.crunchbase.com/feed/", "hashtags": "#стартапы #инвестиции"},
    {"url": "https://sifted.eu/feed", "hashtags": "#стартапы #инвестиции"},

    # Crowdfunding / Kickstarter
    {"url": "https://www.crowdfundinsider.com/feed/", "hashtags": "#краудфандинг #Kickstarter"},
    {"url": "https://backingthefuture.com/feed/", "hashtags": "#краудфандинг #Kickstarter"},

    # Open Source / GitHub
    {"url": "https://github.blog/feed/", "hashtags": "#GitHub #OpenSource"},
    {"url": "https://opensource.com/feed", "hashtags": "#OpenSource #разработка"},

    # Games
    {"url": "https://kotaku.com/rss", "hashtags": "#игры #геймдев"},
    {"url": "https://www.polygon.com/rss/index.xml", "hashtags": "#игры #геймдев"},
    {"url": "https://www.eurogamer.net/?format=rss", "hashtags": "#игры #геймдев"},
    {"url": "https://www.gamesindustry.biz/feed", "hashtags": "#игры #геймдев"},

    # Buddhism
    {"url": "https://www.lionsroar.com/feed/", "hashtags": "#буддизм #медитация"},
    {"url": "https://tricycle.org/feed/", "hashtags": "#буддизм #медитация #осознанность"},
    {"url": "https://plumvillage.org/feed/", "hashtags": "#буддизм #осознанность"},

    # Tibetan Buddhism
    {"url": "https://www.buddhistdoor.net/feed/", "hashtags": "#тибетскийБуддизм #дхарма"},
    {"url": "https://fpmt.org/feed/", "hashtags": "#тибетскийБуддизм #дхарма"},
    {"url": "https://shambhala.com/feed/", "hashtags": "#тибетскийБуддизм #медитация"},
    {"url": "https://www.rigpawiki.org/index.php?title=Special:RecentChanges&feed=rss", "hashtags": "#тибетскийБуддизм #учения"},

    # Tantra / Spirituality
    {"url": "https://www.tantrapath.com/feed/", "hashtags": "#тантра #духовность"},
    {"url": "https://www.mindbodygreen.com/rss.xml", "hashtags": "#тантра #духовность #осознанность"},
    {"url": "https://chopra.com/feed", "hashtags": "#духовность #медитация #аюрведа"},

    # Yoga
    {"url": "https://www.yogajournal.com/feed/", "hashtags": "#йога #духовность"},
    {"url": "https://www.ekhartyoga.com/feed/", "hashtags": "#йога #практика"},
    {"url": "https://www.doyou.com/feed/", "hashtags": "#йога #практика #осознанность"},

    # Sexology
    {"url": "https://www.psychologytoday.com/us/blog/sex-esteem/feed", "hashtags": "#сексология #отношения"},
    {"url": "https://www.refinery29.com/en-us/sex/rss.xml", "hashtags": "#сексология #отношения"},
    {"url": "https://www.vice.com/en/topic/sex/rss", "hashtags": "#сексология"},

    # Psychology
    {"url": "https://www.psychologytoday.com/us/blog/feed", "hashtags": "#психология #саморазвитие"},
    {"url": "https://www.apa.org/news/feed", "hashtags": "#психология #наука"},
    {"url": "https://digest.bps.org.uk/feed/", "hashtags": "#психология #исследования"},
    {"url": "https://neurosciencenews.com/feed/", "hashtags": "#психология #нейронауки"},

    # Science
    {"url": "https://www.sciencedaily.com/rss/all.xml", "hashtags": "#наука #открытия"},
    {"url": "https://www.newscientist.com/feed/home/", "hashtags": "#наука #открытия"},
    {"url": "https://feeds.nature.com/nature/rss/current", "hashtags": "#наука #исследования"},
    {"url": "https://www.quantamagazine.org/feed/", "hashtags": "#наука #математика #физика"},
    {"url": "https://phys.org/rss-feed/", "hashtags": "#наука #физика #открытия"},
]
