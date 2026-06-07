const express = require('express');
const axios = require('axios');
const db = require('../db');

const MPT_BASE_URL = process.env.MPT_BASE_URL || 'http://localhost:8080';

const router = express.Router();

router.post('/looks/:lookId/broll', async (req, res, next) => {
  try {
    const look = await db.get('SELECT * FROM looks WHERE id = ?', [req.params.lookId]);
    if (!look) return res.status(404).json({ error: 'Look not found' });

    const duration = req.body.duration ?? 5;
    const customDescription = req.body.description;
    const description = customDescription || `${look.designer} ${look.season} collection — ${look.title}. Fashion editorial B-Roll.`;

    const insert = await db.run(
      'INSERT INTO broll_clips (look_id, scene_description, duration, status) VALUES (?, ?, ?, ?)',
      [look.id, description, duration, 'pending']
    );

    try {
      const payload = {
        video_subject: description,
        video_aspect: '9:16',
        video_clip_duration: duration,
        video_number: 1,
      };
      const response = await axios.post(`${MPT_BASE_URL}/api/v1/video/generate`, payload);
      const { task_id, status, video_url } = response.data;

      await db.run(
        'UPDATE broll_clips SET mpt_task_id = ?, status = ?, video_url = ? WHERE id = ?',
        [task_id, status || 'generating', video_url || null, insert.lastID]
      );
    } catch (err) {
      await db.run('UPDATE broll_clips SET status = ? WHERE id = ?', ['error', insert.lastID]);
    }

    const clip = await db.get('SELECT * FROM broll_clips WHERE id = ?', [insert.lastID]);
    res.status(201).json(clip);
  } catch (err) {
    next(err);
  }
});

router.get('/looks/:lookId/broll', async (req, res, next) => {
  try {
    const look = await db.get('SELECT * FROM looks WHERE id = ?', [req.params.lookId]);
    if (!look) return res.status(404).json({ error: 'Look not found' });
    const clips = await db.all('SELECT * FROM broll_clips WHERE look_id = ? ORDER BY id DESC', [req.params.lookId]);
    res.json(clips);
  } catch (err) {
    next(err);
  }
});

router.get('/broll/:clipId/status', async (req, res, next) => {
  try {
    let clip = await db.get('SELECT * FROM broll_clips WHERE id = ?', [req.params.clipId]);
    if (!clip) return res.status(404).json({ error: 'Clip not found' });

    if (clip.status === 'generating' && clip.mpt_task_id) {
      try {
        const response = await axios.get(`${MPT_BASE_URL}/api/v1/video/status/${clip.mpt_task_id}`);
        const { status, video_url } = response.data;
        if (status && status !== clip.status) {
          await db.run(
            'UPDATE broll_clips SET status = ?, video_url = ? WHERE id = ?',
            [status, video_url || clip.video_url, req.params.clipId]
          );
          clip = await db.get('SELECT * FROM broll_clips WHERE id = ?', [req.params.clipId]);
        }
      } catch (err) {
        // ignore polling errors, return cached state
      }
    }

    res.json(clip);
  } catch (err) {
    next(err);
  }
});

router.get('/broll/:clipId/download', async (req, res, next) => {
  try {
    const clip = await db.get('SELECT * FROM broll_clips WHERE id = ?', [req.params.clipId]);
    if (!clip) return res.status(404).json({ error: 'Clip not found' });
    if (!clip.video_url) return res.status(400).json({ error: 'Video not ready' });
    res.json({ download_url: clip.video_url });
  } catch (err) {
    next(err);
  }
});

router.delete('/broll/:clipId', async (req, res, next) => {
  try {
    const result = await db.run('DELETE FROM broll_clips WHERE id = ?', [req.params.clipId]);
    if (result.changes === 0) return res.status(404).json({ error: 'Clip not found' });
    res.status(204).send();
  } catch (err) {
    next(err);
  }
});

module.exports = router;
