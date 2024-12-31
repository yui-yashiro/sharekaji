document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("generate-url-btn").addEventListener("click", function () {
        fetch("/generate-invite-url/")
            .then(response => response.json())
            .then(data => {
                const urlElement = document.getElementById("generated-url");
                urlElement.href = data.url;
                urlElement.textContent = data.url;
                document.getElementById("invite-url").style.display = "block";
            })
            .catch(error => console.error("Error generating URL:", error));
    });
});