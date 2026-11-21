# Window measurement

`meaning_mapper.window` measures the rows of one window in a frame the caller
supplies. It is a separate function from the HEXT observation pipeline. That
pipeline is unchanged. Meaning Mapper does not store the frame.

## Frame

A frame is `(frame_id, μ, B, Σ0)`.

- `μ` is a vector of length `D` (the hidden dimension of the rows).
- `B` is `d × D`. It maps a centered row into the frame's coordinates.
- `Σ0` is `d × d` and symmetric positive definite (`is_spd`).
- `d` is the number of rows of `B`. Meaning Mapper does not choose it.

`frame_id` is the content address of `(μ, B, Σ0)`: `frame:sha256:` plus the
SHA-256 hex of the bytes below. `WindowFrame` computes it. A caller does not
pass a name.

MSR distinguishes frames by that string. `ingest` raises `FrameMismatch` when
`measurement.frame_id` is not the runtime's `frame_id` (`src/msr/runtime.py`).
The same string is the same frame, so a free name would let two different
frames share an id.

This is separate from the HEXT pipeline's default `meaning-mapper.default`
(`DEFAULT_FRAME_ID`). That path is unchanged. A window frame does not use it.

`frame_content_id` hashes these bytes, in order:

```text
meaning-mapper.window-frame/1\n
mu <ndim> <dim> <dim> ...\n
<float64 little-endian C-order bytes of mu>
basis <ndim> <dim> ...\n
<bytes of B>
sigma0 <ndim> <dim> ...\n
<bytes of Σ0>
```

Each array is converted to float64 and C order before it is hashed. The shape
in the header is that converted shape.

## Formula

`rows` is `T × D` float64. A point `p` is the half-open range `[start, start + n)`.

- `x̄_p` is the mean of those rows (float64).
- `theta_p = B (x̄_p − μ)`.
- `sigma_p = Σ0 / n_p`.
- `density_p = compute_semantic_density(theta_p)` (RFC-MM003 `D_s`).

`sigma` does not include the spread of the rows inside the point. That spread
is visible as the difference of `theta` when the window is split into more
than one point.

`window_rows` reads the window payload's `points` blob: float32, little-endian,
C order, shape `[length, dimension]`. It checks the uri's sha256 and the byte
count, then converts the values to float64. A mismatch is `WindowMeasureError`.
Nothing is filled in.

`measure_window` refuses a range past the row count, a frame whose `D` is not
the row width, and a non-finite value. Nothing is filled in.

## Meaning of density

窓の行数や測定の証拠量ではなく、frame の座標系で、点の意味表現 theta_p がどれだけ少数の軸に集中しているかを表す指標。D_s = 1 − H / H_max（H は |theta_i| の分布のエントロピー、H_max は一様分布の最大エントロピー）。frame の座標軸に依存するので、異なる frame で計算した density をそのまま比べてはいけない。意味の正しさ、情報量、測定の信頼度を直接表す値ではない。

## Reproducibility

RFC-MM005 asks for bit-identical results. The mean is `numpy.mean` along axis 0
with dtype float64. The product is one `B @ (x̄ − μ)` per point, in point order.
`sigma` is `Σ0` divided by the integer `n`. The matrix product is not rewritten.

Checked with numpy 2.5.1. Its BLAS is Accelerate, not OpenBLAS, so
`OPENBLAS_NUM_THREADS` does not select the library. On this machine, two calls,
a process with `OPENBLAS_NUM_THREADS=1`, and a process with the default thread
count produced the same theta bytes and the same sigma bytes for a `48 × 4096`
window, `d = 64`, both as one point and as one point per row. The same bytes
also held with `VECLIB_MAXIMUM_THREADS=1`. The reduction was left as numpy's
mean and that one product.
