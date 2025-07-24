const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');

const app = express();
const PORT = process.env.PORT || 3000;

app.get('/s', async (req, res) => {
  const asin = req.query.asin;
  if (!asin) return res.status(400).json({ error: 'ASIN required' });

  const url = `https://www.amazon.com/dp/${asin}`;

  try {
    const { data } = await axios.get(url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
      },
    });

    const $ = cheerio.load(data);
    const title = $('#productTitle').text().trim();
    const bullets = $('#feature-bullets li span')
      .map((i, el) => $(el).text().trim())
      .get()
      .filter(Boolean)
      .slice(0, 5); // get first 5 bullets

    res.json({
      asin,
      title: title || 'Title not found',
      bullets: bullets.length ? bullets : ['No bullets found'],
    });
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch product info', details: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
