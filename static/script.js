function generateReport() {
    fetch("/generate-report", { method: "POST" })
        .then(res => res.json())
        .then(data => alert(data.status));
}

function downloadFile(type) {
    window.location.href = `/download/${type}`;
}