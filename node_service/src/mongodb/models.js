const mongoose = require('mongoose');

const profileSchema = new mongoose.Schema({
    username: { type: String, required: true, unique: true },
    full_name: String,
    bio: String,
    followers_count: { type: Number, default: 0 },
    following_count: { type: Number, default: 0 },
    posts_count: { type: Number, default: 0 },
    is_verified: { type: Boolean, default: false },
    is_private: { type: Boolean, default: false },
    discovered_at: { type: Date, default: Date.now }
});

const postSchema = new mongoose.Schema({
    post_id: { type: String, required: true, unique: true },
    owner: { type: String, required: true },
    caption: String,
    media_url: String,
    media_type: { type: String, enum: ['image', 'video', 'reel', 'carousel'] },
    likes: { type: Number, default: 0 },
    comments: { type: Number, default: 0 },
    scraped_at: { type: Date, default: Date.now }
});

module.exports = {
    Profile: mongoose.model('Profile', profileSchema),
    Post: mongoose.model('Post', postSchema)
};
