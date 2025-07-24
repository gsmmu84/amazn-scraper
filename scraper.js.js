// Import dependencies
const express = require('express');
const cors = require('cors');

// Create Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());

// Base route
app.get('/', (req, res) => {
  res.send('✅ Amazon Scraper Server is running!');
});

// Scraper route (replace with real scraping later)
app.get('/s', async (req, res) => {
  const asin = req.query.asin;

  if (!asin) {
    return res.status(400).json({ error: 'ASIN is required in query string (?asin=XXXX)' });
  }

  // For now, just return a mock response
  res.json({
    asin: asin,
    title: 'Example Product Title',
    bullets: ['Bullet 1', 'Bullet 2', 'Bullet 3'],
    description: 'This is a placeholder product description.',
  });

  // 🔧 Later: Replace the above with real Puppeteer scraping logic
});

// Start server
app.listen(PORT, () => {
  console.log(`✅ Server is live on port ${PORT}`);
});
