#!/usr/bin/env python
"""
Test script for inpaint-service.
Usage: python test_inpaint.py [--url http://localhost:8002] [--image-size 512]
"""
import argparse
import io
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw


def create_test_image(size: int = 512) -> tuple[Image.Image, Image.Image]:
    """Create a simple test image and mask."""
    # Create a test image with text-like content
    img = Image.new("RGB", (size, size), color="white")
    draw = ImageDraw.Draw(img)
    
    # Draw some colored rectangles as "content"
    draw.rectangle([50, 50, 150, 150], fill="red", outline="black", width=2)
    draw.rectangle([200, 200, 350, 350], fill="blue", outline="black", width=2)
    draw.rectangle([300, 50, 450, 150], fill="green", outline="black", width=2)
    
    # Create a mask: white = area to inpaint, black = keep
    mask = Image.new("L", (size, size), color=0)  # Start with black (keep all)
    mask_draw = ImageDraw.Draw(mask)
    
    # Make some regions white (to inpaint)
    mask_draw.rectangle([50, 50, 150, 150], fill=255)  # Inpaint red rectangle
    mask_draw.rectangle([300, 50, 450, 150], fill=255)  # Inpaint green rectangle
    
    return img, mask


def test_health(service_url: str) -> bool:
    """Test the /health endpoint."""
    print(f"\n[TEST] Health Check")
    print(f"URL: {service_url}/health")
    try:
        resp = requests.get(f"{service_url}/health", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"✓ Status: {data.get('status')}")
        print(f"✓ Device: {data.get('device')}")
        print(f"✓ Model Loaded: {data.get('model_loaded')}")
        
        if data.get("status") == "initializing":
            print("⚠ Warning: Model is still initializing. Please wait...")
            return False
        return True
    except requests.exceptions.ConnectionError:
        print("✗ Failed to connect. Is the service running?")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_inpaint(service_url: str, image_size: int = 512) -> bool:
    """Test the /inpaint endpoint."""
    print(f"\n[TEST] Inpaint Request")
    print(f"URL: {service_url}/inpaint")
    print(f"Image size: {image_size}x{image_size}")
    
    try:
        # Create test images
        img, mask = create_test_image(image_size)
        
        # Prepare request
        img_buf = io.BytesIO()
        img.save(img_buf, format="PNG")
        img_buf.seek(0)
        
        mask_buf = io.BytesIO()
        mask.save(mask_buf, format="PNG")
        mask_buf.seek(0)
        
        files = {
            "image": ("test_image.png", img_buf, "image/png"),
            "mask": ("test_mask.png", mask_buf, "image/png"),
        }
        
        # Send request (with longer timeout for CPU)
        print("Sending request... (this may take a while on CPU)")
        resp = requests.post(
            f"{service_url}/inpaint",
            files=files,
            timeout=600,  # 10 minutes timeout for CPU inpainting
        )
        resp.raise_for_status()
        
        # Save output
        output_path = Path("inpaint_output.png")
        output_path.write_bytes(resp.content)
        
        # Verify output
        out_img = Image.open(output_path)
        print(f"✓ Response received")
        print(f"✓ Output image size: {out_img.size}")
        print(f"✓ Output saved to: {output_path.absolute()}")
        return True
        
    except requests.exceptions.Timeout:
        print("✗ Request timeout. Service may be overloaded or using CPU.")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Failed to connect. Is the service running?")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test inpaint-service")
    parser.add_argument(
        "--url",
        default="http://localhost:8002",
        help="Service URL (default: http://localhost:8002)",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=512,
        help="Test image size in pixels (default: 512)",
    )
    parser.add_argument(
        "--skip-inpaint",
        action="store_true",
        help="Skip the slow inpaint test, only check health",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("INPAINT SERVICE TEST")
    print("=" * 60)
    print(f"Service URL: {args.url}")
    print(f"Image size: {args.image_size}x{args.image_size}")
    
    # Test health
    health_ok = test_health(args.url)
    
    if not health_ok:
        print("\n⚠ Health check failed. Cannot proceed.")
        sys.exit(1)
    
    # Test inpaint (optional)
    if not args.skip_inpaint:
        inpaint_ok = test_inpaint(args.url, args.image_size)
        if not inpaint_ok:
            print("\n✗ Inpaint test failed.")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
