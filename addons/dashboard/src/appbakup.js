import { useEffect, useState } from "react";
import { Pie, Line } from "react-chartjs-2";
import axios from "axios";
import Chart from "chart.js/auto"; // Import Chart.js

export default function Dashboard() {
  const [logs, setLogs] = useState([]);
  const [logCategories, setLogCategories] = useState({
    critical: 0,
    error: 0,
    info: 0,
    warning: 0,
    unknown: 0
  });
  const [logCounts, setLogCounts] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch logs from Flask API
  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await axios.get("http://127.0.0.1:5000/logs");
      const data = response.data;
      console.log("Fetched logs:", data); // Debugging log to see the data structure

      setLogs(data);

      // Initialize categories and count over time
      const categories = { critical: 0, error: 0, info: 0, warning: 0, unknown: 0 };
      const countOverTime = {};

      data.forEach((log) => {
        const category = log.category || "unknown"; // Fallback to "unknown" if category is missing
        categories[category]++;

        // Count logs by time (assuming timestamp is in seconds)
        const timestamp = new Date(log.timestamp * 1000).toLocaleDateString();
        countOverTime[timestamp] = (countOverTime[timestamp] || 0) + 1;
      });

      setLogCategories(categories);
      setLogCounts(countOverTime);
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error("Error fetching logs:", err);
      setError("Failed to fetch logs. Please check the server or try again later.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(); // Initial fetch
    const interval = setInterval(fetchLogs, 500000); // Update every 500 seconds
    return () => clearInterval(interval);
  }, []);

  // Pie Chart Data
  const pieData = {
    labels: ["Critical", "Error", "Info", "Warning", "Unknown"],
    datasets: [
      {
        data: [
          logCategories.critical,
          logCategories.error,
          logCategories.info,
          logCategories.warning,
          logCategories.unknown,
        ],
        backgroundColor: ["#FF4136", "#FF851B", "#2ECC40", "#FFDC00", "#AAAAAA"],
        hoverOffset: 4,
      },
    ],
  };

  // Line Chart Data (Log Count Over Time)
  const lineData = {
    labels: Object.keys(logCounts),
    datasets: [
      {
        label: "Logs Over Time",
        data: Object.values(logCounts),
        borderColor: "#3498db",
        backgroundColor: "rgba(52, 152, 219, 0.2)",
        fill: true,
        tension: 0.4,
      },
    ],
  };

  // Filter logs based on search input
  const filteredLogs = logs.filter(
    (log) =>
      (log.message && log.message.toLowerCase().includes(search.toLowerCase())) ||
      (log.category && log.category.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="flex">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 text-white p-4">
        <h2 className="text-3xl font-bold mb-6">Dashboard</h2>
        <input
          type="text"
          placeholder="Search logs..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full p-2 rounded mb-4 bg-gray-700 text-white focus:outline-none"
        />
        <div className="text-lg font-medium mb-4">Categories</div>
        <ul>
          <li>Critical: {logCategories.critical}</li>
          <li>Error: {logCategories.error}</li>
          <li>Info: {logCategories.info}</li>
          <li>Warning: {logCategories.warning}</li>
          <li>Unknown: {logCategories.unknown}</li>
        </ul>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 bg-gray-100">
        {loading ? (
          <div className="text-center text-xl text-blue-500">Loading logs...</div>
        ) : error ? (
          <div className="text-center text-xl text-red-500">{error}</div>
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              {/* Pie Chart */}
              <div className="bg-white p-6 rounded-lg shadow-lg">
                <h2 className="text-2xl font-semibold mb-4">Log Category Distribution</h2>
                <Pie data={pieData} />
              </div>

              {/* Line Chart */}
              <div className="bg-white p-6 rounded-lg shadow-lg">
                <h2 className="text-2xl font-semibold mb-4">Logs Over Time</h2>
                <Line data={lineData} />
              </div>
            </div>

            {/* Log Table */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h2 className="text-2xl font-semibold mb-4">Logs</h2>
              <table className="w-full table-auto text-gray-800">
                <thead>
                  <tr className="bg-gray-200">
                    <th className="p-3 text-left">Timestamp</th>
                    <th className="p-3 text-left">Category</th>
                    <th className="p-3 text-left">Message</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.length > 0 ? (
                    filteredLogs.map((log, index) => (
                      <tr key={index} className="border-b hover:bg-gray-50">
                        <td className="p-3">{new Date(log.timestamp * 1000).toLocaleString()}</td>
                        <td
                          className={`p-3 ${
                            log.category === "critical"
                              ? "text-red-600"
                              : log.category === "error"
                              ? "text-orange-500"
                              : log.category === "info"
                              ? "text-green-500"
                              : "text-yellow-500"
                          }`}
                        >
                          {log.category || "Unknown"}
                        </td>
                        <td className="p-3">{log.message || "No message available"}</td> {/* Fallback message */}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="3" className="p-4 text-center">No logs found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

