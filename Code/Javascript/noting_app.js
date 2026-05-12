// app.js

const express = require('express');
const mysql = require('mysql2/promise');
const moment = require('moment');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

const DB_HOST = 'nghia64582.online'
const DB_USER = 'qrucoqmt_nghia64582'
const DB_PASSWORD = 'Nghi@131299'
const DB_NAME = 'qrucoqmt_nghia64582'

const pool = mysql.createPool({
    host: DB_HOST,
    user: DB_USER,
    password: DB_PASSWORD,
    database: DB_NAME
});

app.get('/', (req, res) => {
    res.send('Hello, World, I`m Noting App!');
});

// {
//   "topicId": 1,
//   "tags": ["work", "idea"],
//   "content": "Nội dung ghi chú"
// }
app.post('/notes', async (req, res) => {
    const { topicId, tags = [], content } = req.body;

    if (!content) {
        return res.status(400).json({ message: 'content is required' });
    }

    const conn = await pool.getConnection();
    try {
        await conn.beginTransaction();

        // 1. insert note
        const [noteResult] = await conn.execute(
            `INSERT INTO notes (topic_id, content) VALUES (?, ?)`,
            [topicId || null, content]
        );
        const noteId = noteResult.insertId;

        // 2. handle tags
        for (const tagName of tags) {
            const [tagResult] = await conn.execute(
                `INSERT INTO tags (name)
                 VALUES (?)
                 ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)`,
                [tagName]
            );

            const tagId = tagResult.insertId;

            await conn.execute(
                `INSERT IGNORE INTO note_tags (note_id, tag_id)
                 VALUES (?, ?)`,
                [noteId, tagId]
            );
        }

        await conn.commit();
        res.json({ id: noteId });
    } catch (err) {
        await conn.rollback();
        console.error(err);
        res.status(500).json({ message: 'Internal error' });
    } finally {
        conn.release();
    }
});


// /notes?offset=20&limit=10
app.get('/notes', async (req, res) => {
    const offset = parseInt(req.query.offset) || 0;
    const limit = parseInt(req.query.limit) || 10;

    const [rows] = await pool.execute(
        `SELECT *
         FROM notes
         ORDER BY updated_at DESC
         LIMIT ? OFFSET ?`,
        [limit, offset]
    );

    res.json(rows);
});

// /notes/by-tags?tags=work,idea&offset=0&limit=10
app.get('/notes/by-tags', async (req, res) => {
    const tags = (req.query.tags || '').split(',').filter(Boolean);
    const offset = parseInt(req.query.offset) || 0;
    const limit = parseInt(req.query.limit) || 10;

    if (tags.length === 0) {
        return res.status(400).json({ message: 'tags is required' });
    }

    const placeholders = tags.map(() => '?').join(',');

    const [rows] = await pool.execute(
        `
        SELECT n.*
        FROM notes n
        JOIN note_tags nt ON n.id = nt.note_id
        JOIN tags t ON nt.tag_id = t.id
        WHERE t.name IN (${placeholders})
        GROUP BY n.id
        HAVING COUNT(DISTINCT t.name) = ?
        ORDER BY n.updated_at DESC
        LIMIT ? OFFSET ?
        `,
        [...tags, tags.length, limit, offset]
    );

    res.json(rows);
});

app.get('/notes/:id', async (req, res) => {
    const noteId = req.params.id;

    const [[note]] = await pool.execute(
        `SELECT * FROM notes WHERE id = ?`,
        [noteId]
    );

    if (!note) {
        return res.status(404).json({ message: 'Note not found' });
    }

    const [tags] = await pool.execute(
        `
        SELECT t.id, t.name
        FROM tags t
        JOIN note_tags nt ON t.id = nt.tag_id
        WHERE nt.note_id = ?
        `,
        [noteId]
    );

    // update last_read_at
    await pool.execute(
        `UPDATE notes SET last_read_at = NOW() WHERE id = ?`,
        [noteId]
    );

    res.json({
        ...note,
        tags
    });
});

// {
//   "topicId": 2,
//   "tags": ["backend", "mysql"],
//   "content": "Nội dung mới"
// }

app.put('/notes/:id', async (req, res) => {
    const noteId = req.params.id;
    const { topicId, tags = [], content } = req.body;

    const conn = await pool.getConnection();
    try {
        await conn.beginTransaction();

        // 1. update note
        await conn.execute(
            `UPDATE notes
             SET topic_id = ?, content = ?
             WHERE id = ?`,
            [topicId || null, content, noteId]
        );

        // 2. clear old tags
        await conn.execute(
            `DELETE FROM note_tags WHERE note_id = ?`,
            [noteId]
        );

        // 3. add new tags
        for (const tagName of tags) {
            const [tagResult] = await conn.execute(
                `INSERT INTO tags (name)
                 VALUES (?)
                 ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)`,
                [tagName]
            );

            const tagId = tagResult.insertId;

            await conn.execute(
                `INSERT INTO note_tags (note_id, tag_id)
                 VALUES (?, ?)`,
                [noteId, tagId]
            );
        }

        await conn.commit();
        res.json({ message: 'updated' });
    } catch (err) {
        await conn.rollback();
        console.error(err);
        res.status(500).json({ message: 'Internal error' });
    } finally {
        conn.release();
    }
});



app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});