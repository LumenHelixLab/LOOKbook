const express = require('express');
const router = express.Router();
const db = require('../db');

function serializeLook(row) {
  return {
    ...row,
    images: JSON.parse(row.images || '[]'),
    tags: JSON.parse(row.tags || '[]'),
    broll_url: `/api/looks/${row.id}/broll`,
  };
}

router.get('/looks', async (req, res, next) => {
  try {
    const rows = await db.all('SELECT * FROM looks ORDER BY id DESC');
    res.json(rows.map(serializeLook));
  } catch (err) {
    next(err);
  }
});

router.post('/looks', async (req, res, next) => {
  try {
    const { title, designer, season, images = [], tags = [], status = 'draft' } = req.body;
    const result = await db.run(
      'INSERT INTO looks (title, designer, season, images, tags, status) VALUES (?, ?, ?, ?, ?, ?)',
      [title, designer, season, JSON.stringify(images), JSON.stringify(tags), status]
    );
    const row = await db.get('SELECT * FROM looks WHERE id = ?', [result.lastID]);
    res.status(201).json(serializeLook(row));
  } catch (err) {
    next(err);
  }
});

router.get('/looks/:id', async (req, res, next) => {
  try {
    const row = await db.get('SELECT * FROM looks WHERE id = ?', [req.params.id]);
    if (!row) return res.status(404).json({ error: 'Look not found' });
    res.json(serializeLook(row));
  } catch (err) {
    next(err);
  }
});

router.put('/looks/:id', async (req, res, next) => {
  try {
    const existing = await db.get('SELECT * FROM looks WHERE id = ?', [req.params.id]);
    if (!existing) return res.status(404).json({ error: 'Look not found' });

    const { title, designer, season, images, tags, status } = req.body;
    await db.run(
      'UPDATE looks SET title = ?, designer = ?, season = ?, images = ?, tags = ?, status = ? WHERE id = ?',
      [
        title ?? existing.title,
        designer ?? existing.designer,
        season ?? existing.season,
        JSON.stringify(images ?? JSON.parse(existing.images)),
        JSON.stringify(tags ?? JSON.parse(existing.tags)),
        status ?? existing.status,
        req.params.id,
      ]
    );
    const row = await db.get('SELECT * FROM looks WHERE id = ?', [req.params.id]);
    res.json(serializeLook(row));
  } catch (err) {
    next(err);
  }
});

router.delete('/looks/:id', async (req, res, next) => {
  try {
    const result = await db.run('DELETE FROM looks WHERE id = ?', [req.params.id]);
    if (result.changes === 0) return res.status(404).json({ error: 'Look not found' });
    res.status(204).send();
  } catch (err) {
    next(err);
  }
});

module.exports = router;
