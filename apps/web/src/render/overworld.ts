import type { OverworldMap } from "../types";
import { escapeHtml } from "./dom";

export function renderOverworldMap(overworldMap: OverworldMap | null): string {
  if (!overworldMap || overworldMap.nodes.length === 0) {
    return "<div class=\"chat-empty\">No overworld telemetry available for this expedition.</div>";
  }

  const nodeById = new Map(overworldMap.nodes.map((node) => [node.id, node]));
  const xValues = overworldMap.nodes.map((node) => node.x);
  const yValues = overworldMap.nodes.map((node) => node.y);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const horizontalStep = 120;
  const verticalStep = 92;
  const padding = 36;
  const width = ((maxX - minX) * horizontalStep) + (padding * 2) || 240;
  const height = ((maxY - minY) * verticalStep) + (padding * 2) || 168;

  const getPoint = (nodeId: string): { x: number; y: number } | null => {
    const node = nodeById.get(nodeId);
    if (!node) {
      return null;
    }
    return {
      x: padding + ((node.x - minX) * horizontalStep),
      y: padding + ((node.y - minY) * verticalStep),
    };
  };

  const connections = overworldMap.connections
    .map((connection) => {
      const from = getPoint(connection.location_ids[0]);
      const to = getPoint(connection.location_ids[1]);
      if (!from || !to) {
        return "";
      }
      return `<line class="overworld-map-link${connection.discovered ? " is-discovered" : ""}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" />`;
    })
    .join("");

  const nodes = overworldMap.nodes
    .map((node) => {
      const point = getPoint(node.id);
      if (!point) {
        return "";
      }
      const isCurrent = overworldMap.current_location_id === node.id;
      const label = node.discovered ? escapeHtml(node.name) : "Uncharted";
      return `
        <g class="overworld-map-node${node.discovered ? " is-discovered" : ""}${isCurrent ? " is-current" : ""}" transform="translate(${point.x} ${point.y})">
          <circle class="overworld-map-node-ring" r="18"></circle>
          <circle class="overworld-map-node-core" r="9"></circle>
          <text class="overworld-map-node-label" x="0" y="34" text-anchor="middle">${label}</text>
        </g>
      `;
    })
    .join("");

  const status = overworldMap.current_location_id
    ? `Current route anchor: ${escapeHtml(nodeById.get(overworldMap.current_location_id)?.name ?? "Unknown")}.`
    : "Current location is below the surface; overworld telemetry remains cached.";

  return `
    <div class="overworld-map-card">
      <p class="small overworld-map-note">${status}</p>
      <svg class="overworld-map-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Overworld exploration map">
        <g class="overworld-map-links">${connections}</g>
        <g class="overworld-map-nodes">${nodes}</g>
      </svg>
    </div>
  `;
}
