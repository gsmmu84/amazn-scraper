const express = require('express');
const puppeteer = require('puppeteer');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;

app.use(bodyParser.json());

// Scraper endpoint
app.get('/s', async (req, res) => {
  const { asin } = req.query;

  if (!asin) {
    return res.status(400).json({ error: 'ASIN is required' });
  }

  try {
    const url = `https://www.amazon.com/dp/${asin}`;
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
    const page = await browser.newPage();

    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    );

    await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });

    // Save raw HTML for debugging/caching
    const rawHtml = await page.content();
    const cacheFile = path.join(__dirname, `cache-${asin}.html`);
    fs.writeFileSync(cacheFile, rawHtml);

    // Title
    const title = await page.$eval('#productTitle', el => el.textContent.trim()).catch(() => null);

    // Bullets
    const bullets = await page.$$eval('#feature-bullets li', els =>
      els.map(el => el.textContent.trim()).filter(Boolean)
    );

    // Description (fallback logic)
    let description = await page.$eval('#productDescription', el => el.textContent.trim()).catch(() => null);
    if (!description) {
      description = await page.$eval('.aplus', el => el.textContent.trim()).catch(() => null);
    }
    if (!description) {
      description = "No description available.";
    }

    // Images
    const images = await page.$$eval('img', imgs =>
      imgs
        .map(img => img.src)
        .filter(src => src.includes('amazon') && src.endsWith('.jpg') || src.includes('.png'))
    );

    // Sample reviews
    const reviews = await page.$$eval('.review-text-content span', els =>
      els.map(el => el.textContent.trim()).filter(Boolean)
    );
    const limitedReviews = reviews.slice(0, 5); // First 5 reviews only

    await browser.close();

    res.json({
      asin,
      title,
      bullets,
      description,
      images,
      reviews: limitedReviews,
      aPlusContent: [], // Placeholder for future
      price: null        // Placeholder for future
    });
  } catch (err) {
    console.error('Scraper error:', err);
    res.status(500).json({ error: 'Failed to scrape ASIN page' });
  }
});

// PDF generator
app.post('/generate-pdf', async (req, res) => {
  const htmlEncoded = req.body.html;
  const html = Buffer.from(htmlEncoded, 'base64').toString('utf-8');
  const filename = `pdf-${Date.now()}.pdf`;
  const filepath = path.join(__dirname, filename);

  try {
    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: 'networkidle0' });

    await page.pdf({ path: filepath, format: 'A4' });
    await browser.close();

    const file = fs.readFileSync(filepath);
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename=${filename}`);
    res.send(file);
  } catch (err) {
    console.error(err);
    res.status(500).send('Failed to generate PDF');
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
