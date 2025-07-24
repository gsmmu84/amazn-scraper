const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.send('✅ Scraper server is live and working!');
});

app.get('/s', (req, res) => {
  const { asin } = req.query;

  if (!asin) {
    return res.status(400).json({ error: 'ASIN is required' });
  }

  res.json({
    asin,
    title: `Test Title for ASIN ${asin}`,
    bullets: [
      "This is a test bullet 1",
      "This is a test bullet 2"
    ],
    description: "This is a test product description.",
    reviews: ["Great product!", "Loved it!"],
    images: ["https://via.placeholder.com/300x300"]
  });
});

app.listen(PORT, () => {
  console.log(`✅ Server running on port ${PORT}`);
});

    res.status(500).json({ error: 'Failed to fetch product info', details: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
