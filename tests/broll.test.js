import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';
import request from 'supertest';
import app from '../app.js';
import dbModule from '../db.js';
import axios from 'axios';

const { initSchema, run } = dbModule;

beforeAll(async () => {
  await initSchema();
});

beforeEach(async () => {
  await run('DELETE FROM broll_clips');
  await run('DELETE FROM looks');
  vi.resetAllMocks();
});

describe('B-Roll API', () => {
  it('returns 404 when generating for a non-existent look', async () => {
    const res = await request(app).post('/api/looks/999/broll').send({ duration: 5 });
    expect(res.status).toBe(404);
    expect(res.body.error).toBe('Look not found');
  });

  it('generates B-Roll with auto description', async () => {
    const lookRes = await request(app)
      .post('/api/looks')
      .send({ title: 'Midnight Gala', designer: 'Atelier Noir', season: 'FW25' });
    const look = lookRes.body;

    axios.post.mockResolvedValue({ data: { task_id: 'task-123', status: 'generating', video_url: null } });

    const res = await request(app)
      .post(`/api/looks/${look.id}/broll`)
      .send({ duration: 5 });

    expect(res.status).toBe(201);
    expect(res.body.scene_description).toBe(
      'Atelier Noir FW25 collection — Midnight Gala. Fashion editorial B-Roll.'
    );
    expect(res.body.status).toBe('generating');
    expect(res.body.mpt_task_id).toBe('task-123');
  });

  it('allows custom description override', async () => {
    const lookRes = await request(app)
      .post('/api/looks')
      .send({ title: 'Sunrise', designer: 'Lumen', season: 'SS26' });
    const look = lookRes.body;

    axios.post.mockResolvedValue({ data: { task_id: 'task-456', status: 'generating' } });

    const res = await request(app)
      .post(`/api/looks/${look.id}/broll`)
      .send({ duration: 10, description: 'Custom runway footage' });

    expect(res.status).toBe(201);
    expect(res.body.scene_description).toBe('Custom runway footage');
    expect(res.body.duration).toBe(10);
  });

  it('lists B-Roll clips for a look', async () => {
    const lookRes = await request(app)
      .post('/api/looks')
      .send({ title: 'List Test', designer: 'X', season: 'A' });
    const look = lookRes.body;

    axios.post.mockResolvedValue({ data: { task_id: 't1', status: 'pending' } });
    await request(app).post(`/api/looks/${look.id}/broll`).send({});

    const res = await request(app).get(`/api/looks/${look.id}/broll`);
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].look_id).toBe(look.id);
  });

  it('polls status and transitions to ready', async () => {
    const lookRes = await request(app)
      .post('/api/looks')
      .send({ title: 'Poll', designer: 'Y', season: 'B' });
    const look = lookRes.body;

    axios.post.mockResolvedValue({ data: { task_id: 't2', status: 'generating' } });
    const createRes = await request(app).post(`/api/looks/${look.id}/broll`).send({});
    const clipId = createRes.body.id;

    axios.get.mockResolvedValue({ data: { status: 'ready', video_url: 'http://example.com/vid.mp4' } });

    const pollRes = await request(app).get(`/api/broll/${clipId}/status`);
    expect(pollRes.status).toBe(200);
    expect(pollRes.body.status).toBe('ready');
    expect(pollRes.body.video_url).toBe('http://example.com/vid.mp4');
  });

  it('returns download URL when ready', async () => {
    const lookRes = await request(app)
      .post('/api/looks')
      .send({ title: 'DL', designer: 'Z', season: 'C' });
    const look = lookRes.body;

    axios.post.mockResolvedValue({ data: { task_id: 't3', status: 'ready', video_url: 'http://example.com/dl.mp4' } });
    const createRes = await request(app).post(`/api/looks/${look.id}/broll`).send({});
    const clipId = createRes.body.id;

    const res = await request(app).get(`/api/broll/${clipId}/download`);
    expect(res.status).toBe(200);
    expect(res.body.download_url).toBe('http://example.com/dl.mp4');
  });

  it('deletes a clip', async () => {
    const lookRes = await request(app)
      .post('/api/looks')
      .send({ title: 'Del', designer: 'W', season: 'D' });
    const look = lookRes.body;

    axios.post.mockResolvedValue({ data: { task_id: 't4', status: 'pending' } });
    const createRes = await request(app).post(`/api/looks/${look.id}/broll`).send({});
    const clipId = createRes.body.id;

    const delRes = await request(app).delete(`/api/broll/${clipId}`);
    expect(delRes.status).toBe(204);

    const getRes = await request(app).get(`/api/broll/${clipId}/status`);
    expect(getRes.status).toBe(404);
  });

  it('returns 404 for non-existent clip status', async () => {
    const res = await request(app).get('/api/broll/999/status');
    expect(res.status).toBe(404);
    expect(res.body.error).toBe('Clip not found');
  });
});
