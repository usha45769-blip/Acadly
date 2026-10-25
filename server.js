require('dotenv').config();
const express = require('express');
const path = require('path');
const cors = require('cors');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const pool = require('./db');

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'insecure_dev_secret_change_me';
const N_STUDENTS = 48;
const MAX_MARK = 20;
const GRADE_POINTS = { O: 10, 'A+': 9, A: 8, 'B+': 7, B: 6, C: 5, RA: 0 };

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

function isValidEmail(email) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email); }
function isValidPhone(phone) { return /^[0-9]{10}$/.test(phone); }

function authenticateToken(req, res, next) {
  const header = req.headers['authorization'] || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (!token) return res.status(401).json({ error: 'Missing token.' });
  jwt.verify(token, JWT_SECRET, (err, payload) => {
    if (err) return res.status(403).json({ error: 'Invalid or expired token.' });
    req.userId = payload.id;
    next();
  });
}

async function getUserProfile(userId) {
  const [rows] = await pool.query(
    'SELECT id, name, email, roll_no, required_attendance_pct, notif_idx FROM users WHERE id = ?',
    [userId]
  );
  return rows[0] || null;
}

// ================= AUTH =================

app.post('/api/signup', async (req, res) => {
  try {
    const { name, phone, email, password } = req.body || {};
    if (!name || !name.trim()) return res.status(400).json({ error: 'Name is required.' });
    if (!isValidPhone(phone || '')) return res.status(400).json({ error: 'Enter a valid 10-digit phone number.' });
    if (!isValidEmail(email || '')) return res.status(400).json({ error: 'Enter a valid email address.' });
    if (!password || password.length < 4) return res.status(400).json({ error: 'Password must be at least 4 characters.' });

    const cleanEmail = email.trim().toLowerCase();
    const conn = await pool.getConnection();
    try {
      await conn.beginTransaction();

      const [existing] = await conn.query('SELECT id FROM users WHERE email = ?', [cleanEmail]);
      if (existing.length > 0) {
        await conn.rollback();
        return res.status(409).json({ error: 'An account with this email already exists.' });
      }

      const [takenRows] = await conn.query('SELECT roll_no FROM users WHERE roll_no IS NOT NULL');
      const taken = new Set(takenRows.map((r) => r.roll_no));
      let rollNo = null;
      for (let i = 1; i <= N_STUDENTS; i++) { if (!taken.has(i)) { rollNo = i; break; } }
      if (rollNo === null) {
        await conn.rollback();
        return res.status(409).json({ error: 'All ' + N_STUDENTS + ' student slots are already registered.' });
      }

      const passwordHash = await bcrypt.hash(password, 10);
      const [result] = await conn.query(
        'INSERT INTO users (name, phone, email, password_hash, roll_no) VALUES (?, ?, ?, ?, ?)',
        [name.trim(), phone.trim(), cleanEmail, passwordHash, rollNo]
      );

      const [subjects] = await conn.query('SELECT id, credits FROM subjects');
      for (const s of subjects) {
        await conn.query('INSERT IGNORE INTO attendance (user_id, subject_id) VALUES (?, ?)', [result.insertId, s.id]);
        await conn.query('INSERT IGNORE INTO marks (user_id, subject_id) VALUES (?, ?)', [result.insertId, s.id]);
        await conn.query('INSERT IGNORE INTO grades (user_id, subject_id, credits) VALUES (?, ?, ?)', [result.insertId, s.id, s.credits]);
      }

      await conn.commit();
      const token = jwt.sign({ id: result.insertId }, JWT_SECRET, { expiresIn: '7d' });
      res.status(201).json({ token, user: { id: result.insertId, name: name.trim(), email: cleanEmail, roll_no: rollNo } });
    } catch (err) {
      await conn.rollback();
      throw err;
    } finally {
      conn.release();
    }
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error during signup.' });
  }
});

app.post('/api/login', async (req, res) => {
  try {
    const { email, password } = req.body || {};
    if (!isValidEmail(email || '') || !password) {
      return res.status(400).json({ error: 'Email and password are required.' });
    }
    const cleanEmail = email.trim().toLowerCase();
    const [rows] = await pool.query(
      'SELECT id, name, email, roll_no, password_hash FROM users WHERE email = ?',
      [cleanEmail]
    );
    if (rows.length === 0) return res.status(401).json({ error: 'Incorrect email or password.' });
    const row = rows[0];
    const match = await bcrypt.compare(password, row.password_hash);
    if (!match) return res.status(401).json({ error: 'Incorrect email or password.' });

    const token = jwt.sign({ id: row.id }, JWT_SECRET, { expiresIn: '7d' });
    res.json({ token, user: { id: row.id, name: row.name, email: row.email, roll_no: row.roll_no } });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error during login.' });
  }
});

app.get('/api/me', authenticateToken, async (req, res) => {
  const profile = await getUserProfile(req.userId);
  if (!profile) return res.status(404).json({ error: 'User not found.' });
  res.json({ user: profile });
});

app.put('/api/settings', authenticateToken, async (req, res) => {
  const pct = parseInt(req.body.reqPct, 10);
  if (isNaN(pct) || pct < 0 || pct > 100) return res.status(400).json({ error: 'Enter a percentage between 0 and 100.' });
  await pool.query('UPDATE users SET required_attendance_pct = ? WHERE id = ?', [pct, req.userId]);
  res.json({ ok: true });
});

// ================= SUBJECTS =================

app.get('/api/subjects', authenticateToken, async (req, res) => {
  const [rows] = await pool.query('SELECT id, name, credits FROM subjects ORDER BY id');
  res.json({ subjects: rows });
});

app.put('/api/subjects/:id', authenticateToken, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const name = (req.body.name || '').trim();
  if (!name) return res.status(400).json({ error: 'Subject name cannot be empty.' });
  await pool.query('UPDATE subjects SET name = ? WHERE id = ?', [name, id]);
  res.json({ ok: true });
});

// ================= ATTENDANCE =================

app.get('/api/attendance', authenticateToken, async (req, res) => {
  const [rows] = await pool.query(
    `SELECT s.id AS subject_id, s.name, a.held, a.attended
     FROM subjects s LEFT JOIN attendance a ON a.subject_id = s.id AND a.user_id = ?
     ORDER BY s.id`,
    [req.userId]
  );
  const profile = await getUserProfile(req.userId);
  res.json({
    reqPct: profile.required_attendance_pct,
    notifSubjectId: (profile.notif_idx % rows.length) + 1,
    attendance: rows.map((r) => ({ subjectId: r.subject_id, name: r.name, held: r.held || 0, attended: r.attended || 0 })),
  });
});

app.post('/api/attendance/mark', authenticateToken, async (req, res) => {
  const { subjectId, present } = req.body;
  await pool.query(
    'UPDATE attendance SET held = held + 1, attended = attended + ? WHERE user_id = ? AND subject_id = ?',
    [present ? 1 : 0, req.userId, subjectId]
  );
  await pool.query('UPDATE users SET notif_idx = notif_idx + 1 WHERE id = ?', [req.userId]);
  res.json({ ok: true });
});

app.post('/api/attendance/swap', authenticateToken, async (req, res) => {
  const { actualSubjectId } = req.body;
  await pool.query(
    'UPDATE attendance SET held = held + 1, attended = attended + 1 WHERE user_id = ? AND subject_id = ?',
    [req.userId, actualSubjectId]
  );
  await pool.query('UPDATE users SET notif_idx = notif_idx + 1 WHERE id = ?', [req.userId]);
  res.json({ ok: true });
});

// ================= INTERNAL MARKS =================

app.get('/api/marks', authenticateToken, async (req, res) => {
  const [rows] = await pool.query(
    `SELECT s.id AS subject_id, s.name, m.internal1, m.internal2
     FROM subjects s LEFT JOIN marks m ON m.subject_id = s.id AND m.user_id = ?
     ORDER BY s.id`,
    [req.userId]
  );
  res.json({ maxMark: MAX_MARK, marks: rows });
});

app.put('/api/marks/:subjectId', authenticateToken, async (req, res) => {
  const subjectId = parseInt(req.params.subjectId, 10);
  let { internal1, internal2 } = req.body;
  const clamp = (v) => (v === null || v === '' || v === undefined) ? null : Math.max(0, Math.min(MAX_MARK, parseFloat(v)));
  internal1 = clamp(internal1); internal2 = clamp(internal2);
  await pool.query(
    'UPDATE marks SET internal1 = ?, internal2 = ? WHERE user_id = ? AND subject_id = ?',
    [internal1, internal2, req.userId, subjectId]
  );
  res.json({ ok: true });
});

// ================= SGPA / CGPA =================

app.get('/api/grades', authenticateToken, async (req, res) => {
  const [rows] = await pool.query(
    `SELECT s.id AS subject_id, s.name, g.grade, g.credits
     FROM subjects s LEFT JOIN grades g ON g.subject_id = s.id AND g.user_id = ?
     ORDER BY s.id`,
    [req.userId]
  );
  res.json({ gradePoints: GRADE_POINTS, grades: rows });
});

app.put('/api/grades/:subjectId', authenticateToken, async (req, res) => {
  const subjectId = parseInt(req.params.subjectId, 10);
  const { grade, credits } = req.body;
  if (!(grade in GRADE_POINTS)) return res.status(400).json({ error: 'Invalid grade.' });
  const c = Math.max(1, Math.min(10, parseInt(credits, 10) || 1));
  await pool.query(
    'UPDATE grades SET grade = ?, credits = ? WHERE user_id = ? AND subject_id = ?',
    [grade, c, req.userId, subjectId]
  );
  res.json({ ok: true });
});

app.get('/api/semesters', authenticateToken, async (req, res) => {
  const [rows] = await pool.query(
    'SELECT id, sgpa, credits FROM semesters WHERE user_id = ? ORDER BY id',
    [req.userId]
  );
  res.json({ semesters: rows });
});

app.post('/api/semesters', authenticateToken, async (req, res) => {
  const sgpa = parseFloat(req.body.sgpa);
  const credits = parseInt(req.body.credits, 10);
  if (isNaN(sgpa) || sgpa < 0 || sgpa > 10) return res.status(400).json({ error: 'SGPA must be between 0 and 10.' });
  if (isNaN(credits) || credits <= 0) return res.status(400).json({ error: 'Enter valid credits.' });
  const [result] = await pool.query(
    'INSERT INTO semesters (user_id, sgpa, credits) VALUES (?, ?, ?)',
    [req.userId, sgpa, credits]
  );
  res.status(201).json({ id: result.insertId });
});

app.delete('/api/semesters/:id', authenticateToken, async (req, res) => {
  await pool.query('DELETE FROM semesters WHERE id = ? AND user_id = ?', [req.params.id, req.userId]);
  res.json({ ok: true });
});

// ================= QUESTION BANK =================

app.get('/api/questions', authenticateToken, async (req, res) => {
  const [subjects] = await pool.query('SELECT id, name FROM subjects ORDER BY id');
  const [questions] = await pool.query(
    'SELECT id, subject_id, title, link FROM questions ORDER BY subject_id, id'
  );
  res.json({ subjects, questions });
});

app.post('/api/questions', authenticateToken, async (req, res) => {
  const { subjectId, title, link } = req.body;
  if (!title || !title.trim()) return res.status(400).json({ error: 'Title is required.' });
  const [result] = await pool.query(
    'INSERT INTO questions (subject_id, title, link, added_by) VALUES (?, ?, ?, ?)',
    [subjectId, title.trim(), (link || '').trim() || null, req.userId]
  );
  res.status(201).json({ id: result.insertId });
});

app.delete('/api/questions/:id', authenticateToken, async (req, res) => {
  await pool.query('DELETE FROM questions WHERE id = ?', [req.params.id]);
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`Acadly server running at http://localhost:${PORT}`);
});
