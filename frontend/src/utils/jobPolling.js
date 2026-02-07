export function pollJobStatus(jobId, interval = 5000) {
    return new Promise((resolve, reject) => {
        const poll = setInterval(async () => {
            try {
                const res = await fetch(`/api/job_status/${jobId}`);
                const data = await res.json();

                if (!res.ok) {
                    clearInterval(poll);
                    return reject(data.error || "Failed to get job status");
                }

                if (data.status === "done") {
                    clearInterval(poll);
                    resolve(data);
                } else if (data.status === "error") {
                    clearInterval(poll);
                    reject(data);
                }
            } catch (err) {
                clearInterval(poll);
                reject(err);
            }
        }, interval);
    });
}
