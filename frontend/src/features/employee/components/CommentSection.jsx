import React, { useState } from "react";

import {
    formatDate,
} from "../utils/incidentHelpers";

export default function CommentSection({
    comments = [],
    onSubmit,
    saving = false,
}) {
    const [content, setContent] = useState("");
    const [localError, setLocalError] = useState("");

    const handleSubmit = async (event) => {
        event.preventDefault();

        const trimmed = content.trim();

        if (!trimmed) {
            setLocalError("Please enter a comment.");
            return;
        }

        setLocalError("");

        try {
            await onSubmit(trimmed);
            setContent("");
        } catch {
            // The parent hook/page displays the API error.
        }
    };

    return (
        <section className="employee-section">
            <h2>Comments and updates</h2>

            <div className="employee-comments">
                {comments.length === 0 && (
                    <p className="employee-muted">
                        No comments have been added yet.
                    </p>
                )}

                {comments.map((comment) => (
                    <article
                        key={comment.id}
                        className="employee-comment"
                    >
                        <div className="employee-comment-header">
                            <strong>
                                {comment.authorId
                                    ? `User ${comment.authorId.slice(0, 8)}`
                                    : "User"}
                            </strong>

                            <span>
                                {formatDate(comment.createdAt)}
                            </span>
                        </div>

                        <p>{comment.content}</p>
                    </article>
                ))}
            </div>

            <form
                className="employee-comment-form"
                onSubmit={handleSubmit}
            >
                <label htmlFor="newComment">
                    Add additional information
                </label>

                <textarea
                    id="newComment"
                    rows="3"
                    value={content}
                    placeholder="Describe any additional information..."
                    onChange={(event) =>
                        setContent(event.target.value)
                    }
                    maxLength={2000}
                />

                {localError && (
                    <p className="employee-error">
                        {localError}
                    </p>
                )}

                <button
                    type="submit"
                    disabled={saving}
                    className="employee-button employee-button-primary"
                >
                    {saving ? "Submitting..." : "Add comment"}
                </button>
            </form>
        </section>
    );
}