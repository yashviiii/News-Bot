# Example /search outputs

Generated against the committed `sample.db` (Tesla, Apple Inc, Atlassian). Each block shows the request, the behavior being demonstrated, and the raw JSON returned by `search()`.

All queries use the **default settings**: hybrid retrieval (BM25 + cosine merged via RRF), `threshold=0.65`, `k=5`. Each returned chunk carries a `tier`: `strong` (cosine ≥ 0.72) or `weak` (0.65 ≤ cosine < 0.72). Off-topic queries — top cosine below 0.65 — return an empty `results` array (see `decisions.md` for the hide-over-mislead rationale).

## [Tesla] Clean factual query

Multiple Tesla outlets cover the same factual claim. Hybrid retrieval (default) blends BM25 + cosine via RRF; high-confidence chunks come back with tier=strong, edge cases with tier=weak.

**Query:** `Where will the Tesla Roadster be built?`  
**Company:** `Tesla`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "Where will the Tesla Roadster be built?",
  "company": "Tesla",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [
    {
      "tier": "strong",
      "rrf_score": 0.032522,
      "cosine_score": 0.8152,
      "chunk_text": "Tesla Roadster to be built at Austin Gigafactory\nTesla is adding a sportier vehicle to its lineup, and it'll be built in Austin.\nAdvertisement\nAdvertisement\nUpdated\nTesla is adding a sportier vehicle to its lineup, and it'll be built in Austin.\nAdvertisement",
      "section": "lead",
      "char_start": 0,
      "char_end": 258,
      "chunk_index": 0,
      "source": {
        "article_id": 17,
        "url": "https://www.yahoo.com/news/videos/tesla-roadster-built-austin-gigafactory-011904249.html",
        "title": "Tesla Roadster to be built at Austin Gigafactory",
        "published_at": "2026-05-28",
        "source_domain": "yahoo.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.032018,
      "cosine_score": 0.7759,
      "chunk_text": "News\nTesla unveils juicy new detail on the Roadster and hints at new unveil timeline\nTesla unveiled a juicy new detail on the Roadster, its long-delayed supercar project, and additionally hinted at a new unveiling timeline, as it appears yet another month will pass without seeing the capabilities of the vehicle.\nVice President of Vehicle Engineering at Tesla, Lars Moravy, revealed on the Ride the Lightning podcast that the Roadster will be built at Gigafactory Texas, adding that \u201cyou\u2019ll start to see a lot of things unfold in the next months.\u201d\nWhile we get a good detail on the plant of manufacture, we also get another letdown, as it appears the unveiling event will not take place in May, as CEO Elon Musk hinted during the Earnings Call.",
      "section": "body",
      "char_start": 0,
      "char_end": 745,
      "chunk_index": 0,
      "source": {
        "article_id": 16,
        "url": "https://www.teslarati.com/tesla-unveils-juicy-new-detail-roadster-hints-new-unveil-timeline/",
        "title": "Tesla unveils juicy new detail on the Roadster and hints at new unveil timeline",
        "published_at": "2026-05-26",
        "source_domain": "teslarati.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.031754,
      "cosine_score": 0.803,
      "chunk_text": "Gigafactory Texas, which produces Tesla\u2019s Cybertruck, best-selling Model Y and the new Cybercab, is adding a sportier vehicle to its lineup.\nTesla Inc. executives said this week that the Roadster, which Tesla calls an all-electric supercar, will be built in Texas.\nAdvertisement\nArticle continues below this ad\nChief Designer Franz von Holzhausen and engineering Vice President Lars Moravy said on the Ride the Lightning podcast that Tesla fans should expect to \u201csee a lot of things start to unfold in the next months.\u201d\nThe disclosure signals the possibility of further investment in the sprawling factory east of Austin. Already, the company has said it plans to produce its Optimus robots there and is currently scaling up production of Cybercab, its purpose-built robotaxi. The two-seater was the newest addition since Cybertruck rolled out in late 2023.",
      "section": "body",
      "char_start": 0,
      "char_end": 857,
      "chunk_index": 0,
      "source": {
        "article_id": 15,
        "url": "https://www.statesman.com/business/article/tesla-roadster-gigafactory-texas-austin-22276786.php",
        "title": "Tesla's long-awaited Roadster will be built in Texas, executives say",
        "published_at": "2026-05-27",
        "source_domain": "statesman.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.031746,
      "cosine_score": 0.7985,
      "chunk_text": "Franz von Holzhausen revealed in the Ride the Lightning podcast that the Tesla Roadster will be built at Gigafactory Texas https://t.co/t9Bu9k824Q pic.twitter.com/TT01IWJaFD\n\u2014 TESLARATI (@Teslarati) May 24, 2026\nThe Roadster was first unveiled back in 2017, alongside the Semi, which entered production earlier this year. It was Tesla\u2019s attempt at a true supercar; it would be rare, expensive, and lightning quick, among other incredible capabilities, like potentially hovering for a short period thanks to a collaboration project with SpaceX.\nHowever, the vehicle was set to be delivered in 2020. Parts and supply chain issues due to the COVID-19 pandemic started these delays, and since then, Tesla, and specifically Musk, have wanted to push the capabilities of the Roadster to somewhere the human mind may not be able to currently comprehend.",
      "section": "body",
      "char_start": 746,
      "char_end": 1592,
      "chunk_index": 1,
      "source": {
        "article_id": 16,
        "url": "https://www.teslarati.com/tesla-unveils-juicy-new-detail-roadster-hints-new-unveil-timeline/",
        "title": "Tesla unveils juicy new detail on the Roadster and hints at new unveil timeline",
        "published_at": "2026-05-26",
        "source_domain": "teslarati.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.030769,
      "cosine_score": 0.7403,
      "chunk_text": "READ NEXT: Gigafactory Texas will see production of Tesla robot at \u2018much higher volume\u2019 than California\nRoadster joins Tesla\u2019s Austin-area production plans\nFirst introduced as a prototype in 2006, the original Roadster ended production about six years later when its contract with Lotus Cars, which supplied the Roadster\u2019s chassis, expired.\nAdvertisement\nArticle continues below this ad\nSince then, CEO Elon Musk has publicly pondered when the second generation of the Roadster would arrive. Originally, it was expected to make its debut in 2020, then 2023. And, earlier this spring, Musk said the next generation would be unveiled in late April.\nWant more Statesman?\nIn its first quarter update for investors, Tesla said the sporty EV was in design development.",
      "section": "body",
      "char_start": 858,
      "char_end": 1620,
      "chunk_index": 1,
      "source": {
        "article_id": 15,
        "url": "https://www.statesman.com/business/article/tesla-roadster-gigafactory-texas-austin-22276786.php",
        "title": "Tesla's long-awaited Roadster will be built in Texas, executives say",
        "published_at": "2026-05-27",
        "source_domain": "statesman.com"
      }
    }
  ],
  "tier_summary": {
    "strong": 5,
    "weak": 0,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "corpus": {
    "articles_searched": 22,
    "date_range": [
      "2026-05-25",
      "2026-05-29"
    ],
    "sources": [
      "247wallst.com",
      "arstechnica.com",
      "caranddriver.com",
      "cnbc.com",
      "electrek.co",
      "finance.yahoo.com",
      "forbes.com",
      "fox13news.com",
      "foxnews.com",
      "latimes.com",
      "nbcsandiego.com",
      "notateslaapp.com",
      "statesman.com",
      "techcrunch.com",
      "teslarati.com",
      "wvlt.tv",
      "yahoo.com"
    ]
  },
  "source_coverage": {
    "n_sources": 3,
    "n_articles": 3,
    "multi_source": true,
    "note": "3 independent sources cover this query (3 articles, 5 chunks). Compare each chunk's text + source attribution \u2014 framings may differ.",
    "per_source": [
      {
        "source_domain": "teslarati.com",
        "n_chunks": 2,
        "articles": [
          {
            "article_id": 16,
            "title": "Tesla unveils juicy new detail on the Roadster and hints at new unveil timeline",
            "url": "https://www.teslarati.com/tesla-unveils-juicy-new-detail-roadster-hints-new-unveil-timeline/"
          }
        ]
      },
      {
        "source_domain": "statesman.com",
        "n_chunks": 2,
        "articles": [
          {
            "article_id": 15,
            "title": "Tesla's long-awaited Roadster will be built in Texas, executives say",
            "url": "https://www.statesman.com/business/article/tesla-roadster-gigafactory-texas-austin-22276786.php"
          }
        ]
      },
      {
        "source_domain": "yahoo.com",
        "n_chunks": 1,
        "articles": [
          {
            "article_id": 17,
            "title": "Tesla Roadster to be built at Austin Gigafactory",
            "url": "https://www.yahoo.com/news/videos/tesla-roadster-built-austin-gigafactory-011904249.html"
          }
        ]
      }
    ]
  }
}
```

## [Tesla] Conflict / multi-source coverage

Same legal story covered by several outlets. `source_coverage.multi_source` flags the corroboration; `tier_summary` reports how confident the system is across the returned set.

**Query:** `Tesla Road Rage Driver prison sentence`  
**Company:** `Tesla`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "Tesla Road Rage Driver prison sentence",
  "company": "Tesla",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [
    {
      "tier": "strong",
      "rrf_score": 0.032522,
      "cosine_score": 0.8234,
      "chunk_text": "A man dubbed the \"Tesla Road Rage Driver\" was sentenced to seven years in prison in connection with a violent road rage attack in Hawaii.\nNathaniel Radimak was sentenced Thursday in connection with a 2025 attack involving a mother and her 18-year-old daughter in Honolulu.\nRadimak, who has prior convictions tied to road rage attacks against motorists, acknowledged his actions during sentencing.\n\"I take accountability. I just feel bad about it,\" Radimak said, according to Hawaii News Now. \"It shouldn\u2019t have happened, but I really need a certain kind of treatment that is being prolonged and farther away. It\u2019s not helping me, but I take accountability.\"\nTESLA ROAD-RAGE DRIVER ALLEGEDLY ASSAULTS TEEN, MOM IN HAWAII MONTHS AFTER PRISON RELEASE\nRadimak was charged with one count of unauthorized entry into a motor vehicle and two counts of third-degree assault.",
      "section": "body",
      "char_start": 0,
      "char_end": 865,
      "chunk_index": 0,
      "source": {
        "article_id": 13,
        "url": "https://www.foxnews.com/us/tesla-road-rage-driver-sentenced-seven-years-prison-attacking-mother-daughter-hawaii",
        "title": "'Tesla Road Rage Driver' sentenced to seven years in prison after attacking mother and daughter in Hawaii",
        "published_at": "2026-05-26",
        "source_domain": "foxnews.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.032522,
      "cosine_score": 0.7853,
      "chunk_text": "Tesla driver infamous for California road rage attacks goes to prison for another one in Hawaii\n-\nClick here to listen to this article - Share via\nA Tesla driver who became infamous for a series of road rage attacks captured on camera in Southern California is headed to prison after being convicted of a similar attack in Hawaii.\nNathaniel Radimak, 40, was previously convicted and jailed in Los Angeles over two incidents of road rage, during which he was seen threatening women with a pipe in 2022 and 2023. But after serving less than a year of his five-year sentence, he was paroled and released due to overcrowding.\nThen last May, he was arrested in connection with an attack in Hawaii.\nHonolulu police arrested Radimak after he exchanged words with an 18-year-old woman parking her car on Halekauwila Street, officials said.",
      "section": "body",
      "char_start": 0,
      "char_end": 831,
      "chunk_index": 0,
      "source": {
        "article_id": 12,
        "url": "https://www.latimes.com/california/story/2026-05-26/tesla-road-rage-driver-sentenced",
        "title": "Tesla driver infamous for California road rage attacks goes to prison for another one in Hawaii",
        "published_at": "2026-05-26",
        "source_domain": "latimes.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.031498,
      "cosine_score": 0.7401,
      "chunk_text": "Before his arrest this week, the driver of a black Tesla charged with terrorizing victims across Los Angeles was accused by a woman he dated of threatening to kill her and her family.\nRadimak was accused of getting out of his car and assaulting her and a 35-year-old woman before fleeing.\nHe was charged with one count of unauthorized entry into a car and two counts of assault in the third degree.\nHis attorney did not immediately respond to a request for comment.\nAfter initially pleading not guilty in the case, Radimak entered a plea of no contest in court earlier this year and was sentenced to seven years in prison Thursday.",
      "section": "body",
      "char_start": 832,
      "char_end": 1463,
      "chunk_index": 1,
      "source": {
        "article_id": 12,
        "url": "https://www.latimes.com/california/story/2026-05-26/tesla-road-rage-driver-sentenced",
        "title": "Tesla driver infamous for California road rage attacks goes to prison for another one in Hawaii",
        "published_at": "2026-05-26",
        "source_domain": "latimes.com"
      }
    },
    {
      "tier": "weak",
      "rrf_score": 0.031498,
      "cosine_score": 0.7167,
      "chunk_text": "The two allegedly exchanged words before Radimak got out of the vehicle and assaulted both victims before fleeing the scene, police said. Authorities said he was driving a 2022 gray Tesla with Oregon license plates.\nMOTORIST ARRESTED AFTER ALLEGEDLY TRYING TO RUN DRIVER OF TESLA OFF THE ROAD AT HIGH SPEEDS: REPORT\nRadimak was arrested by Honolulu police the following day.\nThe arrest came just months after Radimak was released from prison after serving less than a year of a five-year sentence tied to a series of violent road rage attacks in Southern California.\nHe was sentenced in 2023 after pleading guilty to assault, vandalism, elder abuse and making criminal threats.\nFox News Digital previously reported that Radimak was known for driving a Tesla and using a pipe to attack the vehicles of his victims, including multiple women.",
      "section": "body",
      "char_start": 1753,
      "char_end": 2592,
      "chunk_index": 2,
      "source": {
        "article_id": 13,
        "url": "https://www.foxnews.com/us/tesla-road-rage-driver-sentenced-seven-years-prison-attacking-mother-daughter-hawaii",
        "title": "'Tesla Road Rage Driver' sentenced to seven years in prison after attacking mother and daughter in Hawaii",
        "published_at": "2026-05-26",
        "source_domain": "foxnews.com"
      }
    },
    {
      "tier": "weak",
      "rrf_score": 0.03031,
      "cosine_score": 0.648,
      "chunk_text": "He pleaded no contest earlier this year.\nJudge Clarissa Malinao said during sentencing that Radimak had failed to seek necessary medical care and continued using illegal substances while on parole for previous convictions.\n\"His history of violence is propensity for violence, and defendant\u2019s voluntary intoxication and discontinuation of medication increase the risk of his dangerousness to self and to the public,\" Malinao said. \"These findings also demonstrate and reinforce that the defendant is indeed a danger to the safety of the public.\"\nWATCH: ROAD RAGE SUSPECT DRAGS MOM OUT OF VEHICLE, BODY-SLAMS HER ON PAVEMENT\nRadimak, 39, was charged after allegedly assaulting an 18-year-old woman and her 35-year-old mother during an incident on May 7, 2025, according to the Honolulu Police Department.\nPolice said the teen was parking downtown when she saw a gray Tesla drive past her.",
      "section": "body",
      "char_start": 866,
      "char_end": 1752,
      "chunk_index": 1,
      "source": {
        "article_id": 13,
        "url": "https://www.foxnews.com/us/tesla-road-rage-driver-sentenced-seven-years-prison-attacking-mother-daughter-hawaii",
        "title": "'Tesla Road Rage Driver' sentenced to seven years in prison after attacking mother and daughter in Hawaii",
        "published_at": "2026-05-26",
        "source_domain": "foxnews.com"
      }
    }
  ],
  "tier_summary": {
    "strong": 3,
    "weak": 2,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "corpus": {
    "articles_searched": 22,
    "date_range": [
      "2026-05-25",
      "2026-05-29"
    ],
    "sources": [
      "247wallst.com",
      "arstechnica.com",
      "caranddriver.com",
      "cnbc.com",
      "electrek.co",
      "finance.yahoo.com",
      "forbes.com",
      "fox13news.com",
      "foxnews.com",
      "latimes.com",
      "nbcsandiego.com",
      "notateslaapp.com",
      "statesman.com",
      "techcrunch.com",
      "teslarati.com",
      "wvlt.tv",
      "yahoo.com"
    ]
  },
  "source_coverage": {
    "n_sources": 2,
    "n_articles": 2,
    "multi_source": true,
    "note": "2 independent sources cover this query (2 articles, 5 chunks). Compare each chunk's text + source attribution \u2014 framings may differ.",
    "per_source": [
      {
        "source_domain": "foxnews.com",
        "n_chunks": 3,
        "articles": [
          {
            "article_id": 13,
            "title": "'Tesla Road Rage Driver' sentenced to seven years in prison after attacking mother and daughter in Hawaii",
            "url": "https://www.foxnews.com/us/tesla-road-rage-driver-sentenced-seven-years-prison-attacking-mother-daughter-hawaii"
          }
        ]
      },
      {
        "source_domain": "latimes.com",
        "n_chunks": 2,
        "articles": [
          {
            "article_id": 12,
            "title": "Tesla driver infamous for California road rage attacks goes to prison for another one in Hawaii",
            "url": "https://www.latimes.com/california/story/2026-05-26/tesla-road-rage-driver-sentenced"
          }
        ]
      }
    ]
  },
  "weak_match_note": "2 of 5 returned chunks fall in the weak band (0.65 \u2264 cosine < 0.72) \u2014 interpret with caution. They're shown because the query has at least one strong match in the result set."
}
```

## [Tesla] Off-topic / no relevant documents

Topic is unrelated to the corpus. Top cosine falls below the 0.65 relevance floor so the system returns an empty `results` array plus a warning. *No documents is a better signal than wrong documents.*

**Query:** `Tesla bakery sourdough recipe`  
**Company:** `Tesla`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "Tesla bakery sourdough recipe",
  "company": "Tesla",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [],
  "tier_summary": {
    "strong": 0,
    "weak": 0,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "warning": "No chunks scored above relevance threshold (0.65). Top cosine match was 0.59 \u2014 the topic appears to be outside the scope of stored articles. Returning no results rather than low-confidence passages.",
  "corpus": {
    "articles_searched": 22,
    "date_range": [
      "2026-05-25",
      "2026-05-29"
    ],
    "sources": [
      "247wallst.com",
      "arstechnica.com",
      "caranddriver.com",
      "cnbc.com",
      "electrek.co",
      "finance.yahoo.com",
      "forbes.com",
      "fox13news.com",
      "foxnews.com",
      "latimes.com",
      "nbcsandiego.com",
      "notateslaapp.com",
      "statesman.com",
      "techcrunch.com",
      "teslarati.com",
      "wvlt.tv",
      "yahoo.com"
    ]
  },
  "source_coverage": {
    "n_sources": 0,
    "n_articles": 0,
    "multi_source": false,
    "note": "No results to summarize.",
    "per_source": []
  },
  "suggestion": "Try re-running /ingest?company=Tesla for newer articles, or refine your query."
}
```

## [Apple Inc] Clean factual query

Apple WWDC + AI coverage from multiple outlets.

**Query:** `What is Apple AAPL planning to announce at WWDC about AI?`  
**Company:** `Apple Inc`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "What is Apple AAPL planning to announce at WWDC about AI?",
  "company": "Apple Inc",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [
    {
      "tier": "strong",
      "rrf_score": 0.032522,
      "cosine_score": 0.803,
      "chunk_text": "Apple Inc. stock (US0378331005): iPhone maker prepares for AI-focused WWDC as investors eye next growth wave\n28.05.2026 - 07:22:45 | ad-hoc-news.deApple Inc. faces rising expectations ahead of its June Worldwide Developers Conference, where the market anticipates major AI announcements for iPhone and Mac. What could this mean for the stock after recent earnings and guidance?\nApple Inc. is heading into its early June Worldwide Developers Conference (WWDC) with investors focused on potential artificial intelligence features for iPhone, iPad and Mac after the company reported its latest quarterly results and outlined capital returns, according to an earnings release published on 05/01/2025 on Apple Investor Relations as of 05/01/2025 and subsequent coverage on 05/02/2025 by Reuters as of 05/02/2025.\nAs of: 28.05.2026\nBy the editorial team \u2013 specialized in equity coverage.",
      "section": "body",
      "char_start": 0,
      "char_end": 881,
      "chunk_index": 0,
      "source": {
        "article_id": 40,
        "url": "https://www.ad-hoc-news.de/boerse/news/ueberblick/apple-inc-stock-us0378331005-iphone-maker-prepares-for-ai-focused-wwdc/69430279",
        "title": "Apple Inc. stock (US0378331005): iPhone maker prepares for AI-focused WWDC as investors eye next gro",
        "published_at": "2026-05-28",
        "source_domain": "ad-hoc-news.de"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.032266,
      "cosine_score": 0.7215,
      "chunk_text": "Read Our Latest Analysis on AAPL\nKey Apple News\nHere are the key news stories impacting Apple this week:\n- Positive Sentiment: Bank of America raised its price target on Apple to $380, saying AI features and a redesigned Siri could drive substantial incremental revenue over the next few years. Article Title\n- Positive Sentiment: Melius Research also boosted its outlook ahead of WWDC 2026, saying Apple could finally show \u201creal AI sizzle,\u201d which has helped fuel expectations for a stronger product cycle. Article Title\n- Positive Sentiment: Multiple pieces highlight Apple\u2019s recent stock strength, including new record highs and growing optimism that the company\u2019s Services business and ecosystem remain resilient even as iPhone growth slows. Article Title\n- Neutral Sentiment: News that Android smartphone makers may be hit harder than Apple by AI memory shortages could be relatively supportive for AAPL by comparison, but it is more of an industry backdrop than a direct catalyst.",
      "section": "body",
      "char_start": 5074,
      "char_end": 6059,
      "chunk_index": 7,
      "source": {
        "article_id": 20,
        "url": "https://www.marketbeat.com/instant-alerts/filing-new-hampshire-trust-sells-4211-shares-of-apple-inc-aapl-2026-05-28/",
        "title": "New Hampshire Trust Sells 4,211 Shares of Apple Inc. $AAPL",
        "published_at": "2026-05-28",
        "source_domain": "marketbeat.com"
      }
    },
    {
      "tier": "weak",
      "rrf_score": 0.03055,
      "cosine_score": 0.6776,
      "chunk_text": "More Apple News\nHere are the key news stories impacting Apple this week:\n- Positive Sentiment: Bank of America raised its price target on Apple to $380, saying AI features and a redesigned Siri could drive substantial incremental revenue over the next few years. Article Title\n- Positive Sentiment: Melius Research also boosted its outlook ahead of WWDC 2026, saying Apple could finally show \u201creal AI sizzle,\u201d which has helped fuel expectations for a stronger product cycle. Article Title\n- Positive Sentiment: Multiple pieces highlight Apple\u2019s recent stock strength, including new record highs and growing optimism that the company\u2019s Services business and ecosystem remain resilient even as iPhone growth slows. Article Title\n- Neutral Sentiment: News that Android smartphone makers may be hit harder than Apple by AI memory shortages could be relatively supportive for AAPL by comparison, but it is more of an industry backdrop than a direct catalyst.",
      "section": "body",
      "char_start": 2873,
      "char_end": 3826,
      "chunk_index": 4,
      "source": {
        "article_id": 18,
        "url": "https://www.marketbeat.com/instant-alerts/filing-apple-inc-aapl-is-middleton-co-inc-mas-2nd-largest-position-2026-05-28/",
        "title": "Apple Inc. $AAPL is Middleton & Co. Inc. MA's 2nd Largest Position",
        "published_at": "2026-05-28",
        "source_domain": "marketbeat.com"
      }
    },
    {
      "tier": "weak",
      "rrf_score": 0.029437,
      "cosine_score": 0.6849,
      "chunk_text": "Apple has chosen to keep Apple TV ad-free, betting that uninterrupted, quality-first viewing strengthens loyalty and ecosystem engagement across more than one billion screens.\nCapital returns add further support. Apple authorized an additional $100 billion buyback and raised its dividend. The upcoming WWDC in June, centered on AI advancements and a more conversational Siri, could lift Services engagement and deepen ecosystem stickiness. Headwinds exist, including rising memory costs, component supply constraints, and tariff exposure, but Apple's scale, cash generation, and ecosystem give it room to absorb them. The forward setup looks comparatively durable and reassuring.\nThe Zacks Consensus Estimate for fiscal 2026 earnings is pegged at $8.74 per share, up 2.6% over the past 30 days, suggesting 17.2% year-over-year growth.\nApple Inc. Price and Consensus\nApple Inc. price-consensus-chart | Apple Inc.",
      "section": "body",
      "char_start": 3847,
      "char_end": 4759,
      "chunk_index": 5,
      "source": {
        "article_id": 25,
        "url": "https://www.tradingview.com/news/zacks:cee278cf0094b:0-netflix-vs-apple-which-streaming-giant-is-the-better-buy-right-now/",
        "title": "Netflix vs. Apple: Which Streaming Giant Is the Better Buy Right Now?",
        "published_at": "2026-05-27",
        "source_domain": "tradingview.com"
      }
    },
    {
      "tier": "weak",
      "rrf_score": 0.029437,
      "cosine_score": 0.6687,
      "chunk_text": "Featured Stories\n- Five stocks we like better than Apple\n- Abercrombie Rallies as Strong Q1 Earnings Extend Winning Streak\n- TeraWulf Bets on Power Infrastructure to Lead AI Build-Out\n- Amazon's Alexa for Shopping Strengthens an Already Strong Bull Case\n- Keysight: The AI and Defense Stock Seeing Big Price Target Boosts\nWant to see what other hedge funds are holding AAPL? Visit HoldingsChannel.com to get the latest 13F filings and insider trades for Apple Inc. (NASDAQ:AAPL - Free Report).\nThis instant news alert was generated by narrative science technology and financial data from MarketBeat in order to provide readers with the fastest reporting and unbiased coverage. Please send any questions or comments about this story to contact@marketbeat.com.\nShould You Invest $1,000 in Apple Right Now?\nBefore you consider Apple, you'll want to hear this.",
      "section": "body",
      "char_start": 8574,
      "char_end": 9430,
      "chunk_index": 11,
      "source": {
        "article_id": 20,
        "url": "https://www.marketbeat.com/instant-alerts/filing-new-hampshire-trust-sells-4211-shares-of-apple-inc-aapl-2026-05-28/",
        "title": "New Hampshire Trust Sells 4,211 Shares of Apple Inc. $AAPL",
        "published_at": "2026-05-28",
        "source_domain": "marketbeat.com"
      }
    }
  ],
  "tier_summary": {
    "strong": 2,
    "weak": 3,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "corpus": {
    "articles_searched": 11,
    "date_range": [
      "2026-05-20",
      "2026-05-28"
    ],
    "sources": [
      "ad-hoc-news.de",
      "finance.yahoo.com",
      "marketbeat.com",
      "tradingview.com",
      "wmur.com"
    ]
  },
  "source_coverage": {
    "n_sources": 3,
    "n_articles": 4,
    "multi_source": true,
    "note": "3 independent sources cover this query (4 articles, 5 chunks). Compare each chunk's text + source attribution \u2014 framings may differ.",
    "per_source": [
      {
        "source_domain": "marketbeat.com",
        "n_chunks": 3,
        "articles": [
          {
            "article_id": 20,
            "title": "New Hampshire Trust Sells 4,211 Shares of Apple Inc. $AAPL",
            "url": "https://www.marketbeat.com/instant-alerts/filing-new-hampshire-trust-sells-4211-shares-of-apple-inc-aapl-2026-05-28/"
          },
          {
            "article_id": 18,
            "title": "Apple Inc. $AAPL is Middleton & Co. Inc. MA's 2nd Largest Position",
            "url": "https://www.marketbeat.com/instant-alerts/filing-apple-inc-aapl-is-middleton-co-inc-mas-2nd-largest-position-2026-05-28/"
          }
        ]
      },
      {
        "source_domain": "ad-hoc-news.de",
        "n_chunks": 1,
        "articles": [
          {
            "article_id": 40,
            "title": "Apple Inc. stock (US0378331005): iPhone maker prepares for AI-focused WWDC as investors eye next gro",
            "url": "https://www.ad-hoc-news.de/boerse/news/ueberblick/apple-inc-stock-us0378331005-iphone-maker-prepares-for-ai-focused-wwdc/69430279"
          }
        ]
      },
      {
        "source_domain": "tradingview.com",
        "n_chunks": 1,
        "articles": [
          {
            "article_id": 25,
            "title": "Netflix vs. Apple: Which Streaming Giant Is the Better Buy Right Now?",
            "url": "https://www.tradingview.com/news/zacks:cee278cf0094b:0-netflix-vs-apple-which-streaming-giant-is-the-better-buy-right-now/"
          }
        ]
      }
    ]
  },
  "weak_match_note": "3 of 5 returned chunks fall in the weak band (0.65 \u2264 cosine < 0.72) \u2014 interpret with caution. They're shown because the query has at least one strong match in the result set."
}
```

## [Apple Inc] Conflict / multi-source coverage

Financial outlets cover Apple stock valuation and AI services from different angles.

**Query:** `Apple AAPL stock valuation and AI service revenue`  
**Company:** `Apple Inc`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "Apple AAPL stock valuation and AI service revenue",
  "company": "Apple Inc",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [
    {
      "tier": "strong",
      "rrf_score": 0.03101,
      "cosine_score": 0.8088,
      "chunk_text": "Apple Inc. (NASDAQ:AAPL) is one of the top tech stocks in billionaire Ken Fisher\u2019s portfolio. On May 8, Wedbush analysts raised their price target of Apple Inc. (NASDAQ:AAPL) stock to $400 from $350, impressed by the company\u2019s entry into the artificial intelligence revolution.\nAccording to the research firm, Apple\u2019s position in the artificial intelligence space is poised to receive a significant boost. That\u2019s in part because 20% of the world population is poised to access AI innovation through the company\u2019s devices.\nSimilarly, the analysts expect the tech giant to start monetizing AI services and storage features, resulting in $15 billion of annual services revenue through additional AI features and storage offerings.\nWedbush also expects strategic partnerships with Alibaba on AI to have a significant impact on strengthening Apple\u2019s prospects in China.",
      "section": "body",
      "char_start": 0,
      "char_end": 864,
      "chunk_index": 0,
      "source": {
        "article_id": 38,
        "url": "https://finance.yahoo.com/sectors/technology/articles/apple-inc-aapl-targets-15b-084136527.html",
        "title": "Apple Inc. (AAPL) Targets $15B Service Revenue via AI",
        "published_at": "2026-05-21",
        "source_domain": "finance.yahoo.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.030018,
      "cosine_score": 0.8194,
      "chunk_text": "The research firm also expects Apple to unveil a significant iPhone redesign in 2027, on its 20th anniversary, as part of the AI revolution.\nApple Inc. (NASDAQ:AAPL) designs, manufactures, and markets consumer electronics, software, and online services. Known for the iPhone, Mac, iPad, and Apple Watch, the company focuses on premium, user-friendly hardware integrated with proprietary operating systems such as iOS and macOS, as well as services like the App Store, Apple Music, and iCloud.\nWhile we acknowledge the potential of AAPL as an investment, we believe certain AI stocks offer greater upside potential and carry less downside risk. If you're looking for an extremely undervalued AI stock that also stands to benefit significantly from Trump-era tariffs and the onshoring trend, see our free report on the best short-term AI stock.",
      "section": "body",
      "char_start": 865,
      "char_end": 1707,
      "chunk_index": 1,
      "source": {
        "article_id": 38,
        "url": "https://finance.yahoo.com/sectors/technology/articles/apple-inc-aapl-targets-15b-084136527.html",
        "title": "Apple Inc. (AAPL) Targets $15B Service Revenue via AI",
        "published_at": "2026-05-21",
        "source_domain": "finance.yahoo.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.029907,
      "cosine_score": 0.849,
      "chunk_text": "(NASDAQ:AAPL) generated $254.9 billion in total net sales, up 16% compared to the first half of fiscal 2025. iPhone revenue for the quarter alone hit a March-record $57 billion, growing 22% year-over-year. Services revenue hit an all-time record of $31 billion, growing 16% year-over-year. Total company gross margin expanded to 49.3%, strongly supported by the Services segment maintaining a gross margin above 76%. This allows Apple to absorb rising advanced chip manufacturing and memory component costs without eroding bottom-line returns. Apple officially confirmed that its installed base of active devices has crossed an all-time high of 2.5 billion active devices globally.\nWhile we acknowledge the potential of AAPL as an investment, we believe certain AI stocks offer greater upside potential and carry less downside risk.",
      "section": "body",
      "char_start": 759,
      "char_end": 1591,
      "chunk_index": 1,
      "source": {
        "article_id": 39,
        "url": "https://finance.yahoo.com/markets/stocks/articles/apple-inc-aapl-top-stock-194310051.html",
        "title": "Apple Inc. (AAPL): A Top Stock Pick by Graham Stephan?",
        "published_at": "2026-05-20",
        "source_domain": "finance.yahoo.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.028629,
      "cosine_score": 0.7612,
      "chunk_text": "NFLX Underperforms AAPL Year-to-date\nConclusion\nWeighing both names, Apple emerges with the clearer edge. Its streaming ambitions sit within a diversified, high-margin Services franchise rather than a single revenue stream, its fiscal third-quarter guidance points to durable double-digit growth, and a premium, ad-free 2026 content slate reinforces ecosystem loyalty. Sizable buybacks, a rising dividend, and stronger year-to-date price performance add support, and its premium valuation looks better justified. Netflix offers a credible growth story and expanding advertising, but front-loaded content costs, competition and price-hike reliance temper its setup. Investors should buy Apple for better upside potential, while holding Netflix or awaiting a better entry point. AAPL carries a Zacks Rank #2 (Buy), while NFLX has a Zacks Rank #3 (Hold). You can see the complete list of today\u2019s Zacks #1 Rank (Strong Buy) stocks here.",
      "section": "body",
      "char_start": 5553,
      "char_end": 6485,
      "chunk_index": 7,
      "source": {
        "article_id": 25,
        "url": "https://www.tradingview.com/news/zacks:cee278cf0094b:0-netflix-vs-apple-which-streaming-giant-is-the-better-buy-right-now/",
        "title": "Netflix vs. Apple: Which Streaming Giant Is the Better Buy Right Now?",
        "published_at": "2026-05-27",
        "source_domain": "tradingview.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.028446,
      "cosine_score": 0.763,
      "chunk_text": "Article Title\n- Positive Sentiment: Multiple pieces highlight Apple\u2019s recent stock strength, including new record highs and growing optimism that the company\u2019s Services business and ecosystem remain resilient even as iPhone growth slows. Article Title\n- Neutral Sentiment: News that Android smartphone makers may be hit harder than Apple by AI memory shortages could be relatively supportive for AAPL by comparison, but it is more of an industry backdrop than a direct catalyst. Article Title\n- Neutral Sentiment: Several articles point to Apple trading near all-time highs and approaching a $5 trillion valuation, reinforcing bullish momentum, though these are mostly commentary rather than fresh company-specific developments. Article Title\n- Negative Sentiment: Some investors remain cautious because iPhone shipment momentum is softening and Apple\u2019s next major growth driver still needs to be proven at WWDC, which leaves room for disappointment if AI announcements underwhelm.",
      "section": "body",
      "char_start": 5834,
      "char_end": 6815,
      "chunk_index": 8,
      "source": {
        "article_id": 19,
        "url": "https://www.marketbeat.com/instant-alerts/filing-apple-inc-aapl-shares-bought-by-rogco-lp-2026-05-28/",
        "title": "Apple Inc. $AAPL Shares Bought by Rogco LP",
        "published_at": "2026-05-28",
        "source_domain": "marketbeat.com"
      }
    }
  ],
  "tier_summary": {
    "strong": 5,
    "weak": 0,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "corpus": {
    "articles_searched": 11,
    "date_range": [
      "2026-05-20",
      "2026-05-28"
    ],
    "sources": [
      "ad-hoc-news.de",
      "finance.yahoo.com",
      "marketbeat.com",
      "tradingview.com",
      "wmur.com"
    ]
  },
  "source_coverage": {
    "n_sources": 3,
    "n_articles": 4,
    "multi_source": true,
    "note": "3 independent sources cover this query (4 articles, 5 chunks). Compare each chunk's text + source attribution \u2014 framings may differ.",
    "per_source": [
      {
        "source_domain": "finance.yahoo.com",
        "n_chunks": 3,
        "articles": [
          {
            "article_id": 38,
            "title": "Apple Inc. (AAPL) Targets $15B Service Revenue via AI",
            "url": "https://finance.yahoo.com/sectors/technology/articles/apple-inc-aapl-targets-15b-084136527.html"
          },
          {
            "article_id": 39,
            "title": "Apple Inc. (AAPL): A Top Stock Pick by Graham Stephan?",
            "url": "https://finance.yahoo.com/markets/stocks/articles/apple-inc-aapl-top-stock-194310051.html"
          }
        ]
      },
      {
        "source_domain": "tradingview.com",
        "n_chunks": 1,
        "articles": [
          {
            "article_id": 25,
            "title": "Netflix vs. Apple: Which Streaming Giant Is the Better Buy Right Now?",
            "url": "https://www.tradingview.com/news/zacks:cee278cf0094b:0-netflix-vs-apple-which-streaming-giant-is-the-better-buy-right-now/"
          }
        ]
      },
      {
        "source_domain": "marketbeat.com",
        "n_chunks": 1,
        "articles": [
          {
            "article_id": 19,
            "title": "Apple Inc. $AAPL Shares Bought by Rogco LP",
            "url": "https://www.marketbeat.com/instant-alerts/filing-apple-inc-aapl-shares-bought-by-rogco-lp-2026-05-28/"
          }
        ]
      }
    ]
  }
}
```

## [Apple Inc] Off-topic / no relevant documents

No coverage in corpus. Threshold gate fires; `results` is empty plus a warning explains why.

**Query:** `Apple kitchen appliance warranty repair`  
**Company:** `Apple Inc`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "Apple kitchen appliance warranty repair",
  "company": "Apple Inc",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [],
  "tier_summary": {
    "strong": 0,
    "weak": 0,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "warning": "No chunks scored above relevance threshold (0.65). Top cosine match was 0.57 \u2014 the topic appears to be outside the scope of stored articles. Returning no results rather than low-confidence passages.",
  "corpus": {
    "articles_searched": 11,
    "date_range": [
      "2026-05-20",
      "2026-05-28"
    ],
    "sources": [
      "ad-hoc-news.de",
      "finance.yahoo.com",
      "marketbeat.com",
      "tradingview.com",
      "wmur.com"
    ]
  },
  "source_coverage": {
    "n_sources": 0,
    "n_articles": 0,
    "multi_source": false,
    "note": "No results to summarize.",
    "per_source": []
  },
  "suggestion": "Try re-running /ingest?company=Apple Inc for newer articles, or refine your query."
}
```

## [Atlassian] Clean factual query

Multiple outlets cover the Atlassian restructuring announcement.

**Query:** `Atlassian outage and AI restructuring strategy`  
**Company:** `Atlassian`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "Atlassian outage and AI restructuring strategy",
  "company": "Atlassian",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [
    {
      "tier": "strong",
      "rrf_score": 0.032258,
      "cosine_score": 0.7941,
      "chunk_text": "- United States\n- /\n- Software\n- /\n- NasdaqGS:TEAM\nAtlassian Restructuring Tests AI Ambitions Service Reliability And Global Growth\n- Atlassian (NasdaqGS:TEAM) has announced a restructuring that includes resource rebalancing and lease consolidation to accelerate profitability and support investment in AI and enterprise sales.\n- A recent public cloud outage affected multiple Atlassian products, raising fresh customer questions about service reliability and operational risk.\n- Improved tone in US China trade relations following the Trump Xi summit has reduced some macro uncertainty for globally exposed software firms, including Atlassian.\nAtlassian, best known for collaboration and workflow tools such as Jira and Confluence, sits at the center of software development and project management for many enterprises. The latest restructuring and renewed focus on AI and larger customers come as software spending priorities continue to shift toward automation, cost efficiency and tools that can link engineering, IT and business teams more tightly.",
      "section": "body",
      "char_start": 0,
      "char_end": 1053,
      "chunk_index": 0,
      "source": {
        "article_id": 71,
        "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/atlassian-restructuring-tests-ai-ambitions-service-reliabili",
        "title": "Atlassian Restructuring Tests AI Ambitions Service Reliability And Global Growth",
        "published_at": "2026-05-23",
        "source_domain": "simplywall.st"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.031746,
      "cosine_score": 0.7851,
      "chunk_text": "In that context, operational execution and customer confidence are likely to be key areas of focus.\nLooking ahead, attention is likely to center on how quickly Atlassian can stabilize service reliability while executing its restructuring plans and AI focused investments. The balance between cost discipline, infrastructure resilience, and product investment may influence how investors assess the company\u2019s competitive position and risk profile from here.\nStay updated on the most important news stories for Atlassian by adding it to your watchlist or portfolio. Alternatively, explore our Community to discover new perspectives on Atlassian.\nWe've flagged 1 risk for Atlassian. See which could impact your investment.\nThe restructuring and recent cloud outage pull investors\u2019 attention straight to Atlassian\u2019s execution risks. Management is reallocating resources and consolidating leases to fund AI-powered products and a larger enterprise sales push, which tilts the business model further toward high-value, large contracts.",
      "section": "body",
      "char_start": 953,
      "char_end": 1982,
      "chunk_index": 1,
      "source": {
        "article_id": 73,
        "url": "https://finance.yahoo.com/markets/stocks/articles/atlassian-outage-restructuring-put-ai-131415178.html",
        "title": "Atlassian Outage And Restructuring Put AI Ambitions Under Investor Scrutiny",
        "published_at": "2026-05-23",
        "source_domain": "finance.yahoo.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.031319,
      "cosine_score": 0.7582,
      "chunk_text": "For you as an investor, these developments put a spotlight on how Atlassian balances profitability goals with service reliability and global expansion. The combination of internal restructuring, recent outage experience and a somewhat clearer US China trade backdrop could influence how the company allocates capital, prices its products and positions NasdaqGS:TEAM within enterprise budgets in the future.\nStay updated on the most important news stories for Atlassian by adding it to your watchlist or portfolio. Alternatively, explore our Community to discover new perspectives on Atlassian.\n4 things going right for Atlassian that this headline doesn't cover.\nFor Atlassian, the current mix of restructuring, outage related questions and a shifting US China trade tone goes straight to the heart of its business model. The resource rebalancing and lease consolidation suggest management is trying to make the AI powered, enterprise focused strategy more cost efficient rather than layering new spend on top of an existing structure.",
      "section": "body",
      "char_start": 1054,
      "char_end": 2089,
      "chunk_index": 1,
      "source": {
        "article_id": 71,
        "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/atlassian-restructuring-tests-ai-ambitions-service-reliabili",
        "title": "Atlassian Restructuring Tests AI Ambitions Service Reliability And Global Growth",
        "published_at": "2026-05-23",
        "source_domain": "simplywall.st"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.031099,
      "cosine_score": 0.8074,
      "chunk_text": "That may help profitability, but it also increases execution risk if critical teams are disrupted just as competitors like Microsoft, ServiceNow and GitLab are pushing hard on their own AI centric workflows. The public cloud outage, even if caused by a third party provider, puts a spotlight on how resilient Atlassian\u2019s multi tenant architecture and incident response processes really are for large enterprises that treat Jira, Confluence and related tools as core infrastructure. At the same time, a less confrontational US China trade backdrop removes one external overhang for globally exposed software vendors, which can matter for long term account planning and data residency decisions.",
      "section": "body",
      "char_start": 2090,
      "char_end": 2783,
      "chunk_index": 2,
      "source": {
        "article_id": 71,
        "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/atlassian-restructuring-tests-ai-ambitions-service-reliabili",
        "title": "Atlassian Restructuring Tests AI Ambitions Service Reliability And Global Growth",
        "published_at": "2026-05-23",
        "source_domain": "simplywall.st"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.030777,
      "cosine_score": 0.7649,
      "chunk_text": "How This Fits Into The Atlassian Narrative\n- The restructuring is aligned with the existing narrative that centers on AI powered cloud growth, because it is explicitly framed as a way to fund AI features and enterprise sales while targeting better profitability.\n- Service reliability concerns after the cloud outage cut across that same catalyst, since AI and workflow automation only reinforce Atlassian\u2019s position if customers trust the uptime and performance of core products.\n- The improving US China trade tone, while mentioned in market commentary, is not a clear focus of the narrative and could be an additional factor influencing how global expansion and large enterprise deal timing play out.\nKnowing what a company is worth starts with understanding its story. Check out one of the top narratives in the Simply Wall St Community for Atlassian to help decide what it's worth to you.",
      "section": "body",
      "char_start": 2784,
      "char_end": 3677,
      "chunk_index": 3,
      "source": {
        "article_id": 71,
        "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/atlassian-restructuring-tests-ai-ambitions-service-reliabili",
        "title": "Atlassian Restructuring Tests AI Ambitions Service Reliability And Global Growth",
        "published_at": "2026-05-23",
        "source_domain": "simplywall.st"
      }
    }
  ],
  "tier_summary": {
    "strong": 5,
    "weak": 0,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "corpus": {
    "articles_searched": 24,
    "date_range": [
      "2026-05-01",
      "2026-05-29"
    ],
    "sources": [
      "247wallst.com",
      "afr.com",
      "atlassian.com",
      "businessinsider.com",
      "cnbc.com",
      "diginomica.com",
      "finance.yahoo.com",
      "fool.com",
      "saastr.com",
      "simplywall.st",
      "stockstory.org",
      "thenewstack.io",
      "williamsf1.com"
    ]
  },
  "source_coverage": {
    "n_sources": 2,
    "n_articles": 2,
    "multi_source": true,
    "note": "2 independent sources cover this query (2 articles, 5 chunks). Compare each chunk's text + source attribution \u2014 framings may differ.",
    "per_source": [
      {
        "source_domain": "simplywall.st",
        "n_chunks": 4,
        "articles": [
          {
            "article_id": 71,
            "title": "Atlassian Restructuring Tests AI Ambitions Service Reliability And Global Growth",
            "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/atlassian-restructuring-tests-ai-ambitions-service-reliabili"
          }
        ]
      },
      {
        "source_domain": "finance.yahoo.com",
        "n_chunks": 1,
        "articles": [
          {
            "article_id": 73,
            "title": "Atlassian Outage And Restructuring Put AI Ambitions Under Investor Scrutiny",
            "url": "https://finance.yahoo.com/markets/stocks/articles/atlassian-outage-restructuring-put-ai-131415178.html"
          }
        ]
      }
    ]
  }
}
```

## [Atlassian] Conflict / multi-source coverage

Multiple financial outlets discuss Atlassian stock and investor narratives.

**Query:** `Atlassian (TEAM) stock and investor sentiment`  
**Company:** `Atlassian`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "Atlassian (TEAM) stock and investor sentiment",
  "company": "Atlassian",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [
    {
      "tier": "strong",
      "rrf_score": 0.031754,
      "cosine_score": 0.8403,
      "chunk_text": "- United States\n- /\n- Software\n- /\n- NasdaqGS:TEAM\nHow AI Disruption Fears and Cloud Optimism Will Shape Atlassian\u2019s (TEAM) Investment Narrative\n- In recent weeks, Atlassian has faced mixed headlines as a laid-off engineer\u2019s detailed YouTube walkthrough of its products stoked competitive and AI-disruption worries, while management highlighted AI-driven cloud growth and restructuring efforts aimed at funding further investment in artificial intelligence and enterprise sales.\n- At the same time, easing Treasury yields, improving sentiment toward SaaS and AI-enabled software, and a more constructive global backdrop have encouraged investors to reassess whether Atlassian\u2019s AI capabilities and partner ecosystem can reinforce, rather than erode, the value of its collaboration platform.\n- With investors weighing AI disruption concerns against stronger sentiment toward SaaS and AI-enabled platforms, we\u2019ll explore how this shapes Atlassian\u2019s investment narrative.\nThe best AI stocks today may lie beyond giants like Nvidia and Microsoft.",
      "section": "body",
      "char_start": 0,
      "char_end": 1042,
      "chunk_index": 0,
      "source": {
        "article_id": 60,
        "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/how-ai-disruption-fears-and-cloud-optimism-will-shape-atlass",
        "title": "How AI Disruption Fears and Cloud Optimism Will Shape Atlassian\u2019s (TEAM) Investment Narrative",
        "published_at": "2026-05-25",
        "source_domain": "simplywall.st"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.030798,
      "cosine_score": 0.8403,
      "chunk_text": "- United States\n- /\n- Software\n- /\n- NasdaqGS:TEAM\nAssessing Atlassian (TEAM) Valuation After A Sharp Disconnect In Recent And 1-Year Share Returns\nRecent share performance puts Atlassian (TEAM) under the microscope\nRecent volatility in Atlassian (TEAM) has pushed the stock into focus, with a near 19% gain over the past month contrasting with a year to date decline of about 45% and a 1 year total return drop of roughly 60%.\nSee our latest analysis for Atlassian.\nAtlassian\u2019s recent 19.4% 30 day share price return and 16.7% 90 day share price return contrast sharply with its 59.5% 1 year total shareholder return decline, suggesting short term momentum is building while longer term holders remain significantly underwater.",
      "section": "quote",
      "char_start": 0,
      "char_end": 728,
      "chunk_index": 0,
      "source": {
        "article_id": 58,
        "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/assessing-atlassian-team-valuation-after-a-sharp-disconnect",
        "title": "Assessing Atlassian (TEAM) Valuation After A Sharp Disconnect In Recent And 1-Year Share Returns",
        "published_at": "2026-05-26",
        "source_domain": "simplywall.st"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.030777,
      "cosine_score": 0.8296,
      "chunk_text": "Atlassian reported revenue of $1.79 billion, up 31.71% year over year, and non-GAAP EPS of $1.75 against a $1.34 consensus. The release also disclosed a $223.83 million restructuring charge tied to workforce rebalancing and lease consolidation.\nAtlassian \u201csoared 29% that evening,\u201d with the stock closing at $88.88 against a prior close of $68.59. Reddit sentiment confirmed the swing, flipping from bearish readings of 22 to 25 in early April to bullish scores of 65 to 72 in early May.\nCEO Mike Cannon-Brookes leaned into the growth framing. Rovo AI usage, Service Collection crossing $1 billion in ARR, and remaining performance obligations of $4.0 billion gave investors a growth story to hold onto.\nThe lesson Ives drew from it is that layoffs alone tanked Atlassian\u2019s stock.",
      "section": "body",
      "char_start": 1802,
      "char_end": 2582,
      "chunk_index": 2,
      "source": {
        "article_id": 57,
        "url": "https://247wallst.com/investing/2026/05/28/analyst-dan-ives-warns-companies-talking-about-job-cuts-are-shooting-themselves-in-the-foot/",
        "title": "Analyst Dan Ives Warns Companies Talking About Job Cuts Are 'Shooting Themselves in the Foot'",
        "published_at": "2026-05-28",
        "source_domain": "247wallst.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.030622,
      "cosine_score": 0.8406,
      "chunk_text": "Find your next quality investment with Simply Wall St's easy and powerful screener, trusted by over 7 million individual investors worldwide.\n-\nAtlassian (NasdaqGS:TEAM) is undergoing a broad restructuring program that includes reallocating resources and consolidating leases to support AI and enterprise sales investments.\n-\nA recent public cloud infrastructure outage led to service degradation across multiple Atlassian products, raising fresh questions about reliability.\n-\nThese operational changes and service disruptions are drawing attention from investors focused on service stability and the company\u2019s long term direction.\nFor investors tracking NasdaqGS:TEAM, these developments come after a period of share price weakness, with the stock down 44.8% year to date and down 58.7% over the past year, closing at $85.42. Multi year returns have also been under pressure, with the stock down 48.6% over three years and down 63.4% over five years.",
      "section": "body",
      "char_start": 0,
      "char_end": 952,
      "chunk_index": 0,
      "source": {
        "article_id": 73,
        "url": "https://finance.yahoo.com/markets/stocks/articles/atlassian-outage-restructuring-put-ai-131415178.html",
        "title": "Atlassian Outage And Restructuring Put AI Ambitions Under Investor Scrutiny",
        "published_at": "2026-05-23",
        "source_domain": "finance.yahoo.com"
      }
    },
    {
      "tier": "strong",
      "rrf_score": 0.030536,
      "cosine_score": 0.8314,
      "chunk_text": "We recently published\nJim Cramer Took A Side On Biggest AI Debate & Discussed These 13 Stocks. Atlassian Corporation (NASDAQ:TEAM) is one of the stocks discussed by Jim Cramer.\nAtlassian Corporation (NASDAQ:TEAM)\u2019s stock is down by 60% over the past year and by 46% year-to-date. Oppenheimer discussed the firm on May 11th as it raised the share price target to $110 from $100 and kept an Outperform rating on the stock. As part of its coverage, the financial firm shared its optimism about Atlassian Corporation (NASDAQ:TEAM)\u2019s AI strategy. More recently, an engineer laid off from the firm appeared in a video on YouTube where he explained the firm\u2019s products in detail. Cramer discussed the appearance:\n\u201cLet me tell you how bad things are. There\u2019s an outfit called TEAM, Atlassian, TEAM is the symbol. Great product.",
      "section": "lead",
      "char_start": 0,
      "char_end": 819,
      "chunk_index": 0,
      "source": {
        "article_id": 59,
        "url": "https://finance.yahoo.com/markets/stocks/articles/jim-cramer-thinks-atlassian-team-230901954.html",
        "title": "Here\u2019s What Jim Cramer Thinks About Atlassian\u2019s (TEAM) YouTube Controversy",
        "published_at": "2026-05-23",
        "source_domain": "finance.yahoo.com"
      }
    }
  ],
  "tier_summary": {
    "strong": 5,
    "weak": 0,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "corpus": {
    "articles_searched": 24,
    "date_range": [
      "2026-05-01",
      "2026-05-29"
    ],
    "sources": [
      "247wallst.com",
      "afr.com",
      "atlassian.com",
      "businessinsider.com",
      "cnbc.com",
      "diginomica.com",
      "finance.yahoo.com",
      "fool.com",
      "saastr.com",
      "simplywall.st",
      "stockstory.org",
      "thenewstack.io",
      "williamsf1.com"
    ]
  },
  "source_coverage": {
    "n_sources": 3,
    "n_articles": 5,
    "multi_source": true,
    "note": "3 independent sources cover this query (5 articles, 5 chunks). Compare each chunk's text + source attribution \u2014 framings may differ.",
    "per_source": [
      {
        "source_domain": "simplywall.st",
        "n_chunks": 2,
        "articles": [
          {
            "article_id": 60,
            "title": "How AI Disruption Fears and Cloud Optimism Will Shape Atlassian\u2019s (TEAM) Investment Narrative",
            "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/how-ai-disruption-fears-and-cloud-optimism-will-shape-atlass"
          },
          {
            "article_id": 58,
            "title": "Assessing Atlassian (TEAM) Valuation After A Sharp Disconnect In Recent And 1-Year Share Returns",
            "url": "https://simplywall.st/stocks/us/software/nasdaq-team/atlassian/news/assessing-atlassian-team-valuation-after-a-sharp-disconnect"
          }
        ]
      },
      {
        "source_domain": "finance.yahoo.com",
        "n_chunks": 2,
        "articles": [
          {
            "article_id": 73,
            "title": "Atlassian Outage And Restructuring Put AI Ambitions Under Investor Scrutiny",
            "url": "https://finance.yahoo.com/markets/stocks/articles/atlassian-outage-restructuring-put-ai-131415178.html"
          },
          {
            "article_id": 59,
            "title": "Here\u2019s What Jim Cramer Thinks About Atlassian\u2019s (TEAM) YouTube Controversy",
            "url": "https://finance.yahoo.com/markets/stocks/articles/jim-cramer-thinks-atlassian-team-230901954.html"
          }
        ]
      },
      {
        "source_domain": "247wallst.com",
        "n_chunks": 1,
        "articles": [
          {
            "article_id": 57,
            "title": "Analyst Dan Ives Warns Companies Talking About Job Cuts Are 'Shooting Themselves in the Foot'",
            "url": "https://247wallst.com/investing/2026/05/28/analyst-dan-ives-warns-companies-talking-about-job-cuts-are-shooting-themselves-in-the-foot/"
          }
        ]
      }
    ]
  }
}
```

## [Atlassian] Off-topic / no relevant documents

Topic is unrelated to the corpus. Empty results + warning instead of low-confidence noise.

**Query:** `Atlassian winery vineyard tasting menu`  
**Company:** `Atlassian`  
**Settings:** `vector_only=false threshold=0.65 k=5`

```json
{
  "query": "Atlassian winery vineyard tasting menu",
  "company": "Atlassian",
  "company_inferred": false,
  "mode": "hybrid",
  "results": [],
  "tier_summary": {
    "strong": 0,
    "weak": 0,
    "strong_threshold": 0.72,
    "relevance_threshold": 0.65
  },
  "warning": "No chunks scored above relevance threshold (0.65). Top cosine match was 0.59 \u2014 the topic appears to be outside the scope of stored articles. Returning no results rather than low-confidence passages.",
  "corpus": {
    "articles_searched": 24,
    "date_range": [
      "2026-05-01",
      "2026-05-29"
    ],
    "sources": [
      "247wallst.com",
      "afr.com",
      "atlassian.com",
      "businessinsider.com",
      "cnbc.com",
      "diginomica.com",
      "finance.yahoo.com",
      "fool.com",
      "saastr.com",
      "simplywall.st",
      "stockstory.org",
      "thenewstack.io",
      "williamsf1.com"
    ]
  },
  "source_coverage": {
    "n_sources": 0,
    "n_articles": 0,
    "multi_source": false,
    "note": "No results to summarize.",
    "per_source": []
  },
  "suggestion": "Try re-running /ingest?company=Atlassian for newer articles, or refine your query."
}
```
