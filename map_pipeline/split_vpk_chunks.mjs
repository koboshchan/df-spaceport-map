#!/usr/bin/env node

import { createHash } from "node:crypto";
import {
  closeSync,
  createReadStream,
  existsSync,
  openSync,
  readSync,
  statSync,
} from "node:fs";
import { mkdir, open, rm } from "node:fs/promises";
import path from "node:path";

const VPK_SIGNATURE = 0x55aa1234;
const EMBEDDED_ARCHIVE = 0x7fff;
const BLOCK_SIZE = 1 << 20;
const UNSIGNED = Buffer.alloc(20);
UNSIGNED.writeUInt32LE(VPK_SIGNATURE, 0);
UNSIGNED.writeUInt32LE(1, 4);

function usage() {
  console.error(
    "Usage: node split_vpk_chunks.mjs <embedded.vpk> <output-dir> [chunk-bytes]",
  );
  process.exit(2);
}

function readCString(buffer, cursor) {
  const end = buffer.indexOf(0, cursor);
  if (end < 0) {
    throw new Error("Truncated VPK directory tree");
  }
  return {
    value: buffer.toString("utf8", cursor, end),
    next: end + 1,
  };
}

function parseDirectory(buffer) {
  const entries = [];
  let cursor = 0;

  while (cursor < buffer.length) {
    const extension = readCString(buffer, cursor);
    cursor = extension.next;
    if (!extension.value) {
      break;
    }

    while (true) {
      const directory = readCString(buffer, cursor);
      cursor = directory.next;
      if (!directory.value) {
        break;
      }

      while (true) {
        const stem = readCString(buffer, cursor);
        cursor = stem.next;
        if (!stem.value) {
          break;
        }
        if (cursor + 18 > buffer.length) {
          throw new Error("Truncated VPK entry metadata");
        }

        const crc = buffer.readUInt32LE(cursor);
        const preloadBytes = buffer.readUInt16LE(cursor + 4);
        const archiveIndex = buffer.readUInt16LE(cursor + 6);
        const offset = buffer.readUInt32LE(cursor + 8);
        const length = buffer.readUInt32LE(cursor + 12);
        const terminator = buffer.readUInt16LE(cursor + 16);
        cursor += 18;

        if (terminator !== 0xffff) {
          throw new Error(`Malformed VPK entry for ${directory.value}/${stem.value}`);
        }
        entries.push({
          extension: extension.value,
          directory: directory.value,
          stem: stem.value,
          crc,
          preloadBytes,
          archiveIndex,
          offset,
          length,
        });
      }
    }
  }

  return entries;
}

function buildDirectory(entries) {
  const groups = new Map();
  for (const entry of entries) {
    if (!groups.has(entry.extension)) {
      groups.set(entry.extension, new Map());
    }
    const directories = groups.get(entry.extension);
    if (!directories.has(entry.directory)) {
      directories.set(entry.directory, []);
    }
    directories.get(entry.directory).push(entry);
  }

  const chunks = [];
  let length = 0;
  const writeString = (value) => {
    const encoded = Buffer.from(value, "utf8");
    chunks.push(encoded, Buffer.from([0]));
    length += encoded.length + 1;
  };

  for (const [extension, directories] of [...groups.entries()].sort(([a], [b]) =>
    a.localeCompare(b),
  )) {
    writeString(extension);
    for (const [directory, directoryEntries] of [...directories.entries()].sort(
      ([a], [b]) => a.localeCompare(b),
    )) {
      writeString(directory);
      for (const entry of directoryEntries.sort((a, b) => a.stem.localeCompare(b.stem))) {
        writeString(entry.stem);
        const metadata = Buffer.alloc(18);
        metadata.writeUInt32LE(entry.crc, 0);
        metadata.writeUInt16LE(0, 4);
        metadata.writeUInt16LE(entry.archiveIndex, 6);
        metadata.writeUInt32LE(entry.newOffset, 8);
        metadata.writeUInt32LE(entry.length, 12);
        metadata.writeUInt16LE(0xffff, 16);
        chunks.push(metadata);
        length += metadata.length;
      }
      chunks.push(Buffer.from([0]));
      length += 1;
    }
    chunks.push(Buffer.from([0]));
    length += 1;
  }
  chunks.push(Buffer.from([0]));
  length += 1;
  return Buffer.concat(chunks, length);
}

async function writeAll(handle, buffer) {
  let offset = 0;
  while (offset < buffer.length) {
    const { bytesWritten } = await handle.write(
      buffer,
      offset,
      buffer.length - offset,
      null,
    );
    if (bytesWritten === 0) {
      throw new Error("Unable to write VPK data");
    }
    offset += bytesWritten;
  }
}

function assignChunks(entries, chunkSize) {
  let currentChunk = 0;
  let currentOffset = 0;
  const chunks = [[]];

  for (const entry of entries) {
    if (currentOffset > 0 && currentOffset + entry.length > chunkSize) {
      currentChunk += 1;
      currentOffset = 0;
      chunks.push([]);
    }
    entry.archiveIndex = currentChunk;
    entry.newOffset = currentOffset;
    currentOffset += entry.length;
    chunks[currentChunk].push(entry);
  }
  return chunks;
}

async function main() {
  const [inputArgument, outputArgument, chunkArgument] = process.argv.slice(2);
  if (!inputArgument || !outputArgument) {
    usage();
  }

  const inputPath = path.resolve(inputArgument);
  const outputDirectory = path.resolve(outputArgument);
  const chunkSize = chunkArgument ? Number(chunkArgument) : 1_000_000_000;
  if (!Number.isSafeInteger(chunkSize) || chunkSize < BLOCK_SIZE) {
    throw new Error("Chunk size must be an integer of at least 1048576 bytes");
  }
  if (!existsSync(inputPath)) {
    throw new Error(`Input VPK does not exist: ${inputPath}`);
  }

  const inputHandle = openSync(inputPath, "r");
  const inputSize = statSync(inputPath).size;
  let header;
  let tree;
  try {
    const headerBuffer = Buffer.alloc(28);
    if (readSync(inputHandle, headerBuffer, 0, headerBuffer.length, 0) !== 28) {
      throw new Error("Truncated VPK header");
    }
    header = {
      signature: headerBuffer.readUInt32LE(0),
      version: headerBuffer.readUInt32LE(4),
      treeSize: headerBuffer.readUInt32LE(8),
      dataSize: headerBuffer.readUInt32LE(12),
    };
    if (header.signature !== VPK_SIGNATURE || header.version !== 2) {
      throw new Error("Expected a VPK v2 input");
    }
    tree = Buffer.alloc(header.treeSize);
    if (readSync(inputHandle, tree, 0, tree.length, 28) !== tree.length) {
      throw new Error("Truncated VPK directory tree");
    }
  } finally {
    closeSync(inputHandle);
  }

  const entries = parseDirectory(tree);
  if (
    entries.some(
      (entry) =>
        entry.archiveIndex !== EMBEDDED_ARCHIVE ||
        entry.preloadBytes !== 0,
    )
  ) {
    throw new Error("Input VPK must contain only embedded entries");
  }
  const dataLength = entries.reduce((total, entry) => total + entry.length, 0);
  if (dataLength !== header.dataSize) {
    throw new Error(
      `VPK entry data (${dataLength}) does not match header (${header.dataSize})`,
    );
  }

  const chunkEntries = assignChunks(entries, chunkSize);
  const chunkEnds = [];
  let chunkEnd = 0;
  for (const chunk of chunkEntries) {
    chunkEnd += chunk.reduce((total, entry) => total + entry.length, 0);
    chunkEnds.push(chunkEnd);
  }
  const outputTree = buildDirectory(entries);
  const embeddedDataOffset = 28 + header.treeSize;
  const baseName = path.basename(inputPath, ".vpk");
  await mkdir(outputDirectory, { recursive: true });

  const mainPath = path.join(outputDirectory, `${baseName}.vpk`);
  const chunkPaths = chunkEntries.map((_, index) =>
    path.join(outputDirectory, `${baseName}_${String(index).padStart(3, "0")}.vpk`),
  );
  for (const stalePath of [mainPath, ...chunkPaths]) {
    if (existsSync(stalePath)) {
      await rm(stalePath);
    }
  }

  const md5Rows = [];
  const source = createReadStream(inputPath, {
    start: embeddedDataOffset,
    end: embeddedDataOffset + dataLength - 1,
    highWaterMark: 8 * 1024 * 1024,
  });
  let sourcePosition = 0;
  let currentChunkIndex = 0;
  let destination = await open(chunkPaths[currentChunkIndex], "w");
  let block = Buffer.allocUnsafe(BLOCK_SIZE);
  let blockLength = 0;
  let blockOffset = 0;
  let destinationOffset = 0;

  const flushBlock = async () => {
    if (blockLength === 0) {
      return;
    }
    await writeAll(destination, block.subarray(0, blockLength));
    const digest = createHash("md5").update(block.subarray(0, blockLength)).digest();
    destinationOffset += blockLength;
    md5Rows.push({
      archiveIndex: currentChunkIndex,
      offset: blockOffset,
      length: blockLength,
      digest,
    });
    blockLength = 0;
    blockOffset = destinationOffset;
  };

  const closeDestination = async () => {
    if (destination) {
      await flushBlock();
      await destination.close();
      destination = null;
    }
  };

  try {
    for await (const readBuffer of source) {
      let readOffset = 0;
      while (readOffset < readBuffer.length) {
        if (sourcePosition >= chunkEnds[currentChunkIndex]) {
          await closeDestination();
          currentChunkIndex += 1;
          if (currentChunkIndex >= chunkPaths.length) {
            throw new Error("Read beyond the last VPK chunk");
          }
          destination = await open(chunkPaths[currentChunkIndex], "w");
          destinationOffset = 0;
          blockOffset = 0;
          blockLength = 0;
        }

        const writable = Math.min(
          readBuffer.length - readOffset,
          chunkEnds[currentChunkIndex] - sourcePosition,
        );
        let bufferOffset = readOffset;
        let remaining = writable;
        while (remaining > 0) {
          const amount = Math.min(remaining, BLOCK_SIZE - blockLength);
          readBuffer.copy(block, blockLength, bufferOffset, bufferOffset + amount);
          blockLength += amount;
          bufferOffset += amount;
          remaining -= amount;
          if (blockLength === BLOCK_SIZE) {
            await flushBlock();
          }
        }
        readOffset += writable;
        sourcePosition += writable;
      }
    }
  } finally {
    await closeDestination();
  }

  if (sourcePosition !== dataLength || md5Rows.length === 0) {
    throw new Error(`Copied ${sourcePosition} bytes, expected ${dataLength}`);
  }
  for (let index = 0; index < chunkPaths.length; index += 1) {
    const expected = chunkEntries[index].reduce(
      (total, entry) => total + entry.length,
      0,
    );
    if (statSync(chunkPaths[index]).size !== expected) {
      throw new Error(`Unexpected size for ${chunkPaths[index]}`);
    }
  }

  const md5Table = Buffer.alloc(md5Rows.length * 28);
  md5Rows.forEach((row, index) => {
    const offset = index * 28;
    md5Table.writeUInt32LE(row.archiveIndex, offset);
    md5Table.writeUInt32LE(row.offset, offset + 4);
    md5Table.writeUInt32LE(row.length, offset + 8);
    row.digest.copy(md5Table, offset + 12);
  });
  const checksums = Buffer.concat([
    createHash("md5").update(outputTree).digest(),
    createHash("md5").update(md5Table).digest(),
  ]);
  const mainHeader = Buffer.alloc(28);
  mainHeader.writeUInt32LE(VPK_SIGNATURE, 0);
  mainHeader.writeUInt32LE(2, 4);
  mainHeader.writeUInt32LE(outputTree.length, 8);
  mainHeader.writeUInt32LE(0, 12);
  mainHeader.writeUInt32LE(md5Table.length, 16);
  mainHeader.writeUInt32LE(checksums.length + 16, 20);
  mainHeader.writeUInt32LE(UNSIGNED.length, 24);
  const directoryChecksum = createHash("md5")
    .update(mainHeader)
    .update(outputTree)
    .update(md5Table)
    .update(checksums)
    .digest();

  const main = await open(mainPath, "w");
  try {
    await writeAll(main, mainHeader);
    await writeAll(main, outputTree);
    await writeAll(main, md5Table);
    await writeAll(main, checksums);
    await writeAll(main, directoryChecksum);
    await writeAll(main, UNSIGNED);
  } finally {
    await main.close();
  }

  console.log(
    JSON.stringify(
      {
        input: inputPath,
        outputDirectory,
        entries: entries.length,
        dataBytes: dataLength,
        chunks: chunkEntries.map((chunk, index) => ({
          file: chunkPaths[index],
          entries: chunk.length,
          bytes: chunk.reduce((total, entry) => total + entry.length, 0),
        })),
        directoryFile: mainPath,
        directoryBytes: statSync(mainPath).size,
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error.stack ?? error.message);
  process.exit(1);
});
