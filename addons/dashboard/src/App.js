import { useEffect, useState } from "react";
import axios from "axios";
import { Pie, Line } from "react-chartjs-2";
import Chart from "chart.js/auto";
import { Card, CardContent } from "@/components/ui/card";

export default function Dashboard() {
  const [logs, setLogs] = useState([]);
  const [logCategories, setLogCategories] = useState({ critical: 0, error: 0, info: 0, warning: 0, unknown: 0 });
  const [logCounts, setLogCounts] = useState({});
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await axios.get("http://127.0.0.1:5000/logs");
      const data = response.data;
      setLogs(data);

      const categories = { critical: 0, error: 0, info: 0, warning: 0, unknown: 0 };
      const countOverTime = {};

      data.forEach((log) => {
        const category = log.category || "unknown";
        categories[category]++;
        const timestamp = new Date(log.timestamp * 1000).toLocaleDateString();
        countOverTime[timestamp] = (countOverTime[timestamp] || 0) + 1;
      });

      setLogCategories(categories);
      setLogCounts(countOverTime);
      setError(null);
    } catch (err) {
      console.error("Error fetching logs:", err);
      setError("Failed to fetch logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 300000);
    return () => clearInterval(interval);
  }, []);

  const pieData = {
    labels: ["Critical", "Error", "Info", "Warning", "Unknown"],
    datasets: [
      {
        data: [logCategories.critical, logCategories.error, logCategories.info, logCategories.warning, logCategories.unknown],
        backgroundColor: ["#E53935", "#FF9800", "#4CAF50", "#FFEB3B", "#9E9E9E"],
        borderWidth: 0,
        hoverOffset: 4,
      },
    ],
  };

  const lineData = {
    labels: Object.keys(logCounts),
    datasets: [
      {
        label: "Logs Over Time",
        data: Object.values(logCounts),
        borderColor: "#03A9F4",
        backgroundColor: "rgba(3, 169, 244, 0.2)",
        fill: true,
        tension: 0.4,
      },
    ],
  };

  return (
    <div className="grid grid-cols-3 gap-4 p-4">
      <Card>
        <CardContent>
          <h2 className="text-xl font-bold">Log Distribution</h2>
          <Pie data={pieData} />
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <h2 className="text-xl font-bold">Activity Timeline</h2>
          <Line data={lineData} />
        </CardContent>
      </Card>

      <Card className="col-span-3">
        <CardContent>
          <h2 className="text-xl font-bold">Log Details</h2>
          <input
            type="text"
            placeholder="Filter Logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full p-3 rounded bg-gray-700 bg-opacity-50 border border-gray-600 focus:outline-none focus:border-blue-500"
          />
          <div className="overflow-x-auto mt-4">
            <table className="min-w-full text-left">
              <thead>
                <tr className="bg-gray-700">
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Message</th>
                </tr>
              </thead>
              <tbody>
                {logs.filter(log => log.message?.toLowerCase().includes(search.toLowerCase()) || log.category?.toLowerCase().includes(search.toLowerCase())).map((log, index) => (
                  <tr key={index} className="border-b border-gray-600 hover:bg-gray-900">
                    <td className="p-3">{new Date(log.timestamp * 1000).toLocaleString()}</td>
                    <td className="p-3 text-red-400">{log.category || "Unknown"}</td>
                    <td className="p-3">{log.message || "No message"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

