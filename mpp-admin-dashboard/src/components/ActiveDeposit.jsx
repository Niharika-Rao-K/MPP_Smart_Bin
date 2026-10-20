
import React, { useCallback, useEffect, useState } from "react";

const DEFAULT_BACKEND_URL = "https://mpp-smart-bin.onrender.com";
const BIN_ID = "BIN001";
const WALLET_ADDRESS = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F";

const ActiveDeposit = ({
  backendUrl = DEFAULT_BACKEND_URL,
}) => {
  const [file, setFile] = useState(null);
  const [reading, setReading] = useState(null);
  const [readingStatus, setReadingStatus] = useState("LOADING");
  const [status, setStatus] = useState("IDLE");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const fetchLatestReading = useCallback(async () => {
    setReadingStatus("LOADING");
    setError("");

    try {
      const response = await fetch(
        `${backendUrl}/api/sensor/weight/latest/${BIN_ID}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not retrieve the sensor reading."
        );
      }

      if (data.status !== "received" || !data.reading_id) {
        setReading(null);
        setReadingStatus("WAITING");
        return;
      }

      setReading(data);
      setReadingStatus("READY");
    } catch (err) {
      setReading(null);
      setReadingStatus("ERROR");
      setError(err.message || "Could not connect to the backend.");
    }
  }, [backendUrl]);

  useEffect(() => {
    fetchLatestReading();
  }, [fetchLatestReading]);

  const handleFileChange = (event) => {
    setFile(event.target.files?.[0] || null);
  };

  const handleDepositSubmit = async (event) => {
    event.preventDefault();

    if (!file) {
      setError("Please select an image of the item first.");
      return;
    }

    if (!reading?.reading_id) {
      setError(
        "No unused load-cell reading is available. Take a new measurement first."
      );
      return;
    }

    setStatus("SCANNING");
    setResult(null);
    setError("");

    const formData = new FormData();
    formData.append("image", file);
    formData.append("label", "");
    formData.append("reading_id", reading.reading_id);
    formData.append("wallet_address", WALLET_ADDRESS);
    formData.append("bin_id", BIN_ID);

    try {
      const response = await fetch(
        `${backendUrl}/api/rag/evaluate`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Deposit evaluation failed."
        );
      }

      setResult(data);
      setStatus(data.status === "SUCCESS" ? "SUCCESS" : "REJECTED");

      // This reading was claimed by the backend. Remove it from
      // the current UI and ask the sensor for another reading.
      setReading(null);
      setReadingStatus("WAITING");
      setFile(null);

      const imageInput = document.getElementById("deposit-item-image");
      if (imageInput) imageInput.value = "";

      await fetchLatestReading();
    } catch (err) {
      setStatus("IDLE");
      setError(err.message || "Could not submit the deposit.");

      // The server may have claimed the reading before a later
      // processing error. Refresh instead of assuming it is reusable.
      await fetchLatestReading();
    }
  };

  const busy = status === "SCANNING";

  return (
    <div
      style={{
        maxWidth: "600px",
        margin: "20px auto",
        padding: "20px",
        border: "1px solid #ccc",
        borderRadius: "8px",
      }}
    >
      <h2>♻️ Smart Recycling Deposit Terminal</h2>

      <p>
        <strong>Bin:</strong> {BIN_ID}
      </p>

      <div
        style={{
          marginBottom: "20px",
          padding: "12px",
          border: "1px solid #ddd",
          borderRadius: "6px",
        }}
      >
        <h3>Load-cell measurement</h3>

        {readingStatus === "LOADING" && (
          <p>Checking for an available sensor reading...</p>
        )}

        {readingStatus === "WAITING" && (
          <p>
            No unused measurement is available. Place the item on
            the connected load cell and take a new measurement.
          </p>
        )}

        {readingStatus === "ERROR" && (
          <p role="alert">{error}</p>
        )}

        {readingStatus === "READY" && reading && (
          <>
            <p>
              <strong>Measured weight:</strong>{" "}
              {Number(reading.weight_g).toFixed(2)} g
            </p>
            <p>
              <strong>Sensor:</strong> {reading.sensor_id}
            </p>
            <p>
              <strong>Reading ID:</strong>{" "}
              <code>{reading.reading_id}</code>
            </p>
            <p>
              <strong>Measurement time:</strong>{" "}
              {reading.created_at
                ? new Date(reading.created_at).toLocaleString()
                : "Unavailable"}
            </p>
          </>
        )}

        <button
          type="button"
          onClick={fetchLatestReading}
          disabled={busy || readingStatus === "LOADING"}
          style={{ padding: "8px 12px" }}
        >
          Refresh Sensor Reading
        </button>
      </div>

      <form
        onSubmit={handleDepositSubmit}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "15px",
        }}
      >
        <div>
          <label
            htmlFor="deposit-item-image"
            style={{
              display: "block",
              marginBottom: "5px",
              fontWeight: "bold",
            }}
          >
            Item photo
          </label>

          <input
            id="deposit-item-image"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            disabled={busy}
            required
          />
        </div>

        <button
          type="submit"
          disabled={
            busy ||
            readingStatus !== "READY" ||
            !reading?.reading_id
          }
          style={{
            padding: "12px",
            background: "#2e7d32",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          {busy
            ? "Processing item..."
            : "Evaluate Deposit"}
        </button>
      </form>

      {busy && (
        <p style={{ marginTop: "20px", color: "#0288d1" }}>
          Analyzing the image, verifying the measured weight,
          and evaluating recycling eligibility...
        </p>
      )}

      {error && (
        <p role="alert" style={{ color: "#c62828" }}>
          {error}
        </p>
      )}

      {result && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            borderRadius: "6px",
            background:
              status === "SUCCESS" ? "#e8f5e9" : "#ffebee",
          }}
        >
          <h3>
            {status === "SUCCESS"
              ? "✅ Item Verified"
              : "❌ Item Rejected"}
          </h3>

          <ul style={{ listStyle: "none", paddingLeft: 0 }}>
            <li>
              <strong>Detected item:</strong>{" "}
              {result.predicted_label}
            </li>
            <li>
              <strong>Measured weight:</strong>{" "}
              {result.stable_weight_g} g
            </li>
            <li>
              <strong>Hardware signal:</strong>{" "}
              {result.hardware_route_signal}
            </li>
            <li>
              <strong>Decision:</strong>{" "}
              {result.fusion_result?.action ||
                result.fusion_result?.decision ||
                result.status}
            </li>
            <li>
              <strong>Reward status:</strong>{" "}
              {result.web3_reward?.status || "Not available"}
            </li>
            <li>
              <strong>Tokens calculated:</strong>{" "}
              {result.calculated_credits ?? 0}
            </li>
          </ul>

          {result.web3_reward?.tx_hash && (
            <p>
              <strong>Transaction hash:</strong>{" "}
              <code>{result.web3_reward.tx_hash}</code>
            </p>
          )}

          {result.web3_reward?.explorer_url && (
            <p>
              <a
                href={result.web3_reward.explorer_url}
                target="_blank"
                rel="noreferrer"
              >
                View blockchain transaction
              </a>
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default ActiveDeposit;
