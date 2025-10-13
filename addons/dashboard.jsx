import { useEffect, useState } from "react";

export default function Dashboard() {
    const [logs, setLogs] = useState([]);

    // Fetch logs from Flask API
    const fetchLogs = async () => {
        try {
            const response = await fetch("http://127.0.0.1:5000/logs");
            const data = await response.json();
            setLogs(data);
        } catch (error) {
            console.error("Error fetching logs:", error);
        }
    };

    useEffect(() => {
        fetchLogs();
        const interval = setInterval(fetchLogs, 5000); // Refresh every 5 sec
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">🔍 SIEM Log Dashboard</h1>
            <table className="w-full border border-gray-300">
                <thead>
                    <tr className="bg-gray-200">
                        <th className="border p-2">Timestamp</th>
                        <th className="border p-2">Log Message</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.length > 0 ? (
                        logs.map((log, index) => (
                            <tr key={index} className="border">
                                <td className="p-2">{new Date(log.timestamp * 1000).toLocaleString()}</td>
                                <td className="p-2">{log.log}</td>
                            </tr>
                        ))
                    ) : (
                        <tr>
                            <td colSpan="2" className="p-4 text-center">No logs found.</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}
