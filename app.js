
// ================= FOOD IMAGE ANALYZER =================

const form = document.getElementById("analyzeForm");

if (form) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const input = document.getElementById("foodImage");
        const error = document.getElementById("error");
        const result = document.getElementById("result");
        const loading = document.getElementById("loading");

        error.hidden = true;
        result.hidden = true;

        if (!input.files.length) {
            error.textContent = "Please select a food image.";
            error.hidden = false;
            return;
        }

        const file = input.files[0];

        // Create a temporary browser preview of the uploaded image
        const imagePreview = URL.createObjectURL(file);

        const data = new FormData();
        data.append("food_image", file);

        loading.hidden = false;

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                body: data
            });

            const body = await response.json();

            if (!response.ok) {
                throw new Error(body.error || "Analysis failed.");
            }

            const n = body.nutrition || {};
            const h = body.health;

            // Display food image and prediction
            result.innerHTML = `
                <div class="row g-4">

                    <div class="col-md-5">

                        <img
                            class="food-preview"
                            src="${imagePreview}"
                            alt="Uploaded food"
                            style="width:100%; max-height:350px; object-fit:cover; border-radius:15px;"
                        >

                        <h3 class="h4 mt-3">
                            ${escapeHtml(body.food || "Unknown food")}
                        </h3>

                        <span class="badge text-bg-success">
                            Model confidence: ${escapeHtml(body.confidence ?? 0)}%
                        </span>

                        <p class="small text-muted mt-2">
                            ${escapeHtml(body.note || "")}
                        </p>

                    </div>

                    <div class="col-md-7">

                        <h3 class="h5">Nutrition Estimate</h3>

                        <p class="text-muted small">
                            Reference serving:
                            ${escapeHtml(n.serving || "Not available")}
                        </p>

                        ${n.warning ? `
                            <div class="alert alert-warning">
                                ${escapeHtml(n.warning)}
                            </div>
                        ` : ""}

                        <div class="result-grid">

                            ${metric("Calories", (n.calories ?? 0) + " kcal")}
                            ${metric("Protein", (n.protein ?? 0) + " g")}
                            ${metric("Carbs", (n.carbs ?? 0) + " g")}
                            ${metric("Fat", (n.fat ?? 0) + " g")}
                            ${metric("Fiber", (n.fiber ?? 0) + " g")}
                            ${metric("Sugar", (n.sugar ?? 0) + " g")}

                        </div>

                        ${h ? `
                            <div class="mt-3 p-3 rounded-3 bg-light">

                                <strong>
                                    Health Assessment:
                                    ${escapeHtml(h.label || "Not available")}
                                </strong>

                                <div>
                                    ${h.score == null
                                        ? "No score available"
                                        : "Educational score: " + escapeHtml(h.score) + "/100"
                                    }
                                </div>

                                <p class="mb-0 small">
                                    ${escapeHtml(h.advice || "")}
                                </p>

                            </div>
                        ` : `
                            <div class="alert alert-info mt-3">
                                Health assessment is unavailable for this food.
                            </div>
                        `}

                    </div>

                </div>
            `;

            result.hidden = false;

        } catch (e) {

            URL.revokeObjectURL(imagePreview);

            error.textContent = e.message;
            error.hidden = false;

        } finally {

            loading.hidden = true;

        }
    });
}


// ================= NUTRITION METRIC CARD =================

function metric(label, value) {
    return `
        <div class="metric">
            <span class="small text-muted">
                ${escapeHtml(label)}
            </span>
            <strong>
                ${escapeHtml(value)}
            </strong>
        </div>
    `;
}


// ================= HTML SECURITY =================

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    }[c]));
}
