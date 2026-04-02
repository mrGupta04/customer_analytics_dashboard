const { useEffect, useMemo, useRef, useState } = React;

const API_BASE = window.DASHBOARD_API_BASE || "http://127.0.0.1:8000";
const CURRENCY = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
});

function toBool(value) {
    if (typeof value === "boolean") {
        return value;
    }
    return String(value).toLowerCase() === "true";
}

function RevenueChart({ data }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (!canvasRef.current) {
            return;
        }

        const labels = data.map((row) => row.order_year_month);
        const values = data.map((row) => Number(row.total_revenue || 0));

        const chartData = {
            labels,
            datasets: [
                {
                    label: "Completed Revenue",
                    data: values,
                    borderColor: "#127369",
                    backgroundColor: "rgba(18, 115, 105, 0.15)",
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: "#127369",
                    borderWidth: 2.5,
                    tension: 0.2,
                    fill: true,
                },
            ],
        };

        if (chartRef.current) {
            chartRef.current.data = chartData;
            chartRef.current.update();
            return;
        }

        chartRef.current = new Chart(canvasRef.current, {
            type: "line",
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                return CURRENCY.format(context.parsed.y || 0);
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        ticks: {
                            callback(value) {
                                return CURRENCY.format(value);
                            },
                        },
                    },
                },
            },
        });
    }, [data]);

    useEffect(() => {
        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, []);

    return (
        <div className="chart-wrap">
            <canvas ref={canvasRef} />
        </div>
    );
}

function CategoryChart({ data }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (!canvasRef.current) {
            return;
        }

        const labels = data.map((row) => row.category || "Unknown");
        const values = data.map((row) => Number(row.total_revenue || 0));

        if (chartRef.current) {
            chartRef.current.data.labels = labels;
            chartRef.current.data.datasets[0].data = values;
            chartRef.current.update();
            return;
        }

        chartRef.current = new Chart(canvasRef.current, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Revenue by Category",
                        data: values,
                        backgroundColor: [
                            "#127369",
                            "#1b9f92",
                            "#5ec3ba",
                            "#e2812f",
                            "#f0b273",
                            "#8c4b0f",
                        ],
                        borderRadius: 8,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                return CURRENCY.format(context.parsed.y || 0);
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        ticks: {
                            callback(value) {
                                return CURRENCY.format(value);
                            },
                        },
                    },
                },
            },
        });
    }, [data]);

    useEffect(() => {
        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, []);

    return (
        <div className="chart-wrap">
            <canvas ref={canvasRef} />
        </div>
    );
}

function DashboardApp() {
    const [status, setStatus] = useState({
        message: "Loading dashboard data...",
        isError: false,
    });
    const [revenueData, setRevenueData] = useState([]);
    const [categoryData, setCategoryData] = useState([]);
    const [topCustomers, setTopCustomers] = useState([]);
    const [regions, setRegions] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [sortBy, setSortBy] = useState({ key: "total_spend", direction: "desc" });

    const [draftStart, setDraftStart] = useState("");
    const [draftEnd, setDraftEnd] = useState("");
    const [appliedStart, setAppliedStart] = useState("");
    const [appliedEnd, setAppliedEnd] = useState("");

    useEffect(() => {
        async function loadData() {
            try {
                const [revenue, customers, categories, regionRows] = await Promise.all([
                    fetch(`${API_BASE}/api/revenue`).then((res) => {
                        if (!res.ok) {
                            throw new Error("Failed to load revenue");
                        }
                        return res.json();
                    }),
                    fetch(`${API_BASE}/api/top-customers`).then((res) => {
                        if (!res.ok) {
                            throw new Error("Failed to load top customers");
                        }
                        return res.json();
                    }),
                    fetch(`${API_BASE}/api/categories`).then((res) => {
                        if (!res.ok) {
                            throw new Error("Failed to load categories");
                        }
                        return res.json();
                    }),
                    fetch(`${API_BASE}/api/regions`).then((res) => {
                        if (!res.ok) {
                            throw new Error("Failed to load regions");
                        }
                        return res.json();
                    }),
                ]);

                setRevenueData(revenue);
                setTopCustomers(customers);
                setCategoryData(categories);
                setRegions(regionRows);
                setStatus({ message: "Data loaded successfully.", isError: false });
            } catch (error) {
                console.error(error);
                setStatus({
                    message:
                        "Something went wrong while loading dashboard data. Check backend/API status.",
                    isError: true,
                });
            }
        }

        loadData();
    }, []);

    const filteredRevenue = useMemo(() => {
        let rows = [...revenueData];
        if (appliedStart) {
            rows = rows.filter((row) => row.order_year_month >= appliedStart);
        }
        if (appliedEnd) {
            rows = rows.filter((row) => row.order_year_month <= appliedEnd);
        }
        return rows;
    }, [revenueData, appliedStart, appliedEnd]);

    const visibleCustomers = useMemo(() => {
        let rows = [...topCustomers];

        if (searchTerm.trim()) {
            const term = searchTerm.trim().toLowerCase();
            rows = rows.filter((row) => {
                const name = String(row.name || "").toLowerCase();
                const region = String(row.region || "").toLowerCase();
                return name.includes(term) || region.includes(term);
            });
        }

        rows.sort((a, b) => {
            const left = a[sortBy.key];
            const right = b[sortBy.key];
            const direction = sortBy.direction === "asc" ? 1 : -1;

            if (sortBy.key === "total_spend") {
                return (Number(left || 0) - Number(right || 0)) * direction;
            }
            if (sortBy.key === "churned") {
                return (Number(toBool(left)) - Number(toBool(right))) * direction;
            }
            return String(left || "").localeCompare(String(right || "")) * direction;
        });

        return rows;
    }, [topCustomers, searchTerm, sortBy]);

    function toggleSort(key) {
        setSortBy((current) => {
            if (current.key === key) {
                return {
                    key,
                    direction: current.direction === "asc" ? "desc" : "asc",
                };
            }
            return {
                key,
                direction: key === "total_spend" ? "desc" : "asc",
            };
        });
    }

    function applyRevenueFilter() {
        setAppliedStart(draftStart);
        setAppliedEnd(draftEnd);
    }

    return (
        <>
            <div className="background-shape shape-a"></div>
            <div className="background-shape shape-b"></div>
            <header className="top-header">
                <div className="top-inner">
                    <div className="brand-block">
                        <span className="brand-title">MultiplierAI</span>
                        <span className="brand-subtitle">Revenue Intelligence Portal</span>
                    </div>
                    <nav className="top-nav">
                        <a href="#revenue">Revenue</a>
                        <a href="#customers">Customers</a>
                        <a href="#categories">Categories</a>
                        <a href="#regions">Regions</a>
                    </nav>
                </div>
            </header>
            <main className="container">
                <header className="hero">
                    <p className="eyebrow">Technical Round Dashboard</p>
                    <h1>Customer and Revenue Intelligence</h1>
                    <p
                        className={
                            status.isError ? "status status-error" : "status status-loading"
                        }
                    >
                        {status.message}
                    </p>
                </header>

                <section className="panel" id="revenue">
                    <div className="panel-title-row">
                        <h2>Revenue Trend</h2>
                        <div className="controls">
                            <label>
                                Start
                                <input
                                    type="month"
                                    value={draftStart}
                                    onChange={(event) => setDraftStart(event.target.value)}
                                />
                            </label>
                            <label>
                                End
                                <input
                                    type="month"
                                    value={draftEnd}
                                    onChange={(event) => setDraftEnd(event.target.value)}
                                />
                            </label>
                            <button type="button" onClick={applyRevenueFilter}>
                                Apply
                            </button>
                        </div>
                    </div>
                    <RevenueChart data={filteredRevenue} />
                </section>

                <section className="panel" id="customers">
                    <div className="panel-title-row">
                        <h2>Top Customers</h2>
                        <label className="search-box">
                            Search
                            <input
                                type="search"
                                placeholder="Name or region"
                                value={searchTerm}
                                onChange={(event) => setSearchTerm(event.target.value)}
                            />
                        </label>
                    </div>
                    <div className="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th onClick={() => toggleSort("name")}>Name</th>
                                    <th onClick={() => toggleSort("region")}>Region</th>
                                    <th onClick={() => toggleSort("total_spend")}>Total Spend</th>
                                    <th onClick={() => toggleSort("churned")}>Churned</th>
                                </tr>
                            </thead>
                            <tbody>
                                {visibleCustomers.map((row) => {
                                    const churned = toBool(row.churned);
                                    return (
                                        <tr key={row.customer_id}>
                                            <td>{row.name || "Unknown"}</td>
                                            <td>{row.region || "Unknown"}</td>
                                            <td>{CURRENCY.format(Number(row.total_spend || 0))}</td>
                                            <td>
                                                <span
                                                    className={
                                                        churned ? "pill pill-yes" : "pill pill-no"
                                                    }
                                                >
                                                    {churned ? "Yes" : "No"}
                                                </span>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section className="panel split">
                    <div id="categories">
                        <h2>Category Breakdown</h2>
                        <CategoryChart data={categoryData} />
                    </div>
                    <div id="regions">
                        <h2>Region Summary</h2>
                        <div className="table-wrap">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Region</th>
                                        <th>Customers</th>
                                        <th>Orders</th>
                                        <th>Total Revenue</th>
                                        <th>Avg / Customer</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {regions.map((row) => (
                                        <tr key={row.region}>
                                            <td>{row.region || "Unknown"}</td>
                                            <td>{Number(row.number_of_customers || 0)}</td>
                                            <td>{Number(row.number_of_orders || 0)}</td>
                                            <td>{CURRENCY.format(Number(row.total_revenue || 0))}</td>
                                            <td>
                                                {CURRENCY.format(
                                                    Number(row.average_revenue_per_customer || 0)
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>
            </main>
            <footer className="site-footer">
                <div className="footer-inner">
                    <p>Built for the Data Analyst + Fullstack Technical Assignment.</p>
                    <p>Data source: processed CSV outputs from the Python analytics pipeline.</p>
                </div>
            </footer>
        </>
    );
}

ReactDOM.createRoot(document.getElementById("root")).render(<DashboardApp />);
