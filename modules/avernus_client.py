import httpx
import tempfile

class AvernusClient:
    """This is the client for the avernus API server"""
    def __init__(self, url, port=6969):
        self.url = url
        self.port = port
        self.base_url = f"{self.url}:{self.port}"

    async def ace_music(self, prompt, lyrics, audio_duration=None, guidance_scale=None, infer_step=None,
                        omega_scale=None, actual_seeds=None):
        """This takes a prompt and lyrics and returns a song"""
        url = f"http://{self.base_url}/ace_generate"
        data = {"prompt": prompt,
                "lyrics": lyrics,
                "audio_duration": audio_duration,
                "guidance_scale": guidance_scale,
                "infer_step": infer_step,
                "omega_scale": omega_scale,
                "actual_seeds": actual_seeds}

        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                # Save the returned binary video content
                #with open("output.wav", "wb") as f:
                #    f.write(response.content)
                return response.content
            else:
                print(f"ACE STEP ERROR: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def check_status(self):
        """Attempts to contact the avernus server and returns a dict with status information from the server"""
        url = f"http://{self.base_url}/status"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"STATUS ERROR: {response.status_code}, Response: {response.text}")
                return {"ERROR": response.text}
        except Exception as e:
            print(f"status ERROR: {e}")
            return {"ERROR": str(e)}

    async def flux_fill_image(self, prompt, image=None, model_name=None, width=None,
                              height=None, steps=None, batch_size=None, guidance_scale=None, mask_image=None,
                              strength=None, lora_name=None, seed=None):
        """This takes a prompt, and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/flux_fill_generate"
        data = {"prompt": prompt,
                "image": image,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "guidance_scale": guidance_scale,
                "mask_image": mask_image,
                "strength": strength,
                "seed": seed}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"FLUX FILL ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def flux_image(self, prompt, image=None, model_name=None, lora_name=None, width=None, height=None, steps=None,
                         batch_size=None, strength=None, ip_adapter_image=None, ip_adapter_strength=None, seed=None,
                         guidance_scale=None):
        """This takes a prompt and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/flux_generate"
        data = {"prompt": prompt,
                "image": image,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "strength": strength,
                "ip_adapter_strength": ip_adapter_strength,
                "ip_adapter_image": ip_adapter_image,
                "seed": seed,
                "guidance_scale": guidance_scale}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"FLUX ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def flux_inpaint_image(self, prompt, image=None, model_name=None, width=None,
                                 height=None, steps=None, batch_size=None, guidance_scale=None, mask_image=None,
                                 strength=None, lora_name=None, seed=None):
        """This takes a prompt, and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/flux_inpaint_generate"
        data = {"prompt": prompt,
                "image": image,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "guidance_scale": guidance_scale,
                "mask_image": mask_image,
                "strength": strength,
                "seed": seed}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"FLUX INPAINT ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def flux_kontext(self, prompt, image=None, model_name=None, lora_name=None, width=None, height=None, steps=None,
                           batch_size=None, controlnet_image=None, controlnet_processor=None,
                           ip_adapter_image=None, ip_adapter_strength=None, seed=None, guidance_scale=None):
        """This takes a prompt and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/flux_kontext_generate"
        data = {"prompt": prompt,
                "image": image,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "controlnet_image": controlnet_image,
                "controlnet_processor": controlnet_processor,
                "ip_adapter_strength": ip_adapter_strength,
                "ip_adapter_image": ip_adapter_image,
                "seed": seed,
                "guidance_scale": guidance_scale}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"FLUX KONTEXT ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def list_flux_loras(self):
        """Fetches the list of flux LoRA filenames from the server."""
        url = f"http://{self.base_url}/list_flux_loras"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return response.json().get("loras", [])
            else:
                print(f"LIST FLUX LORAS ERROR: {response.status_code}, Response: {response.text}")
                return {"ERROR": response.text}
        except Exception as e:
            print(f"list_flux_loras ERROR: {e}")
            return {"ERROR": str(e)}

    async def list_qwen_image_loras(self):
        """Fetches the list of qwen_image LoRA filenames from the server."""
        url = f"http://{self.base_url}/list_qwen_image_loras"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return response.json().get("loras", [])
            else:
                print(f"LIST QWEN IMAGE LORAS ERROR: {response.status_code}, Response: {response.text}")
                return {"ERROR": response.text}
        except Exception as e:
            print(f"list_qwen_image_loras ERROR: {e}")
            return {"ERROR": str(e)}

    async def list_sdxl_controlnets(self):
        """Fetches the list of sdxl controlnets from the server."""
        url = f"http://{self.base_url}/list_sdxl_controlnets"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return response.json().get("sdxl_controlnets", [])
            else:
                print(f"LIST SDXL CONTROLNETS ERROR: {response.status_code}, Response: {response.text}")
                return {"ERROR": response.text}
        except Exception as e:
            print(f"list_sdxl_controlnets ERROR: {e}")
            return {"ERROR": str(e)}

    async def list_sdxl_loras(self):
        """Fetches the list of sdxl LoRA filenames from the server."""
        url = f"http://{self.base_url}/list_sdxl_loras"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return response.json().get("loras", [])
            else:
                print(f"LIST SDXL LORAS ERROR: {response.status_code}, Response: {response.text}")
                return {"ERROR": response.text}
        except Exception as e:
            print(f"list_sdxl_loras ERROR: {e}")
            return {"ERROR": str(e)}

    async def list_sdxl_schedulers(self):
        """Fetches the list of sdxl schedulers from the server."""
        url = f"http://{self.base_url}/list_sdxl_schedulers"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return response.json().get("schedulers", [])
            else:
                print(f"LIST SDXL SCHEDULERS ERROR: {response.status_code}, Response: {response.text}")
                return {"ERROR": response.text}
        except Exception as e:
            print(f"list_sdxl_schedulers ERROR: {e}")
            return {"ERROR": str(e)}

    async def llm_chat(self, prompt, model_name=None, messages=None):
        """This takes a prompt, and optionally a model name and chat history, then returns a response"""
        url = f"http://{self.base_url}/llm_chat"
        data = {"prompt": prompt, "model_name": model_name, "messages": messages}

        try:
            async with httpx.AsyncClient(timeout=3600.0) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                print(f"LLM ERROR: {response.status_code}, Response: {response.text}")
                return {"LLM ERROR": response.text}
        except Exception as e:
            print(f"EXCEPTION ERROR: {e}")
            return {"ERROR": str(e)}

    async def qwen_image_image(self, prompt, negative_prompt=None, image=None, model_name=None, lora_name=None,
                               width=None, height=None, steps=None, batch_size=None, strength=None, seed=None,
                               true_cfg_scale=None):
        """This takes a prompt and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/qwen_image_generate"
        data = {"prompt": prompt,
                "negative_prompt": negative_prompt,
                "image": image,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "strength": strength,
                "seed": seed,
                "true_cfg_scale": true_cfg_scale}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"FLUX ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def qwen_image_inpaint_image(self, prompt, negative_prompt=None, image=None, model_name=None, width=None,
                                       height=None, steps=None, batch_size=None, true_cfg_scale=None, mask_image=None,
                                       strength=None, lora_name=None, seed=None):
        """This takes a prompt, and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/qwen_image_inpaint_generate"
        data = {"prompt": prompt,
                "negative_prompt": negative_prompt,
                "image": image,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "true_cfg_scale": true_cfg_scale,
                "mask_image": mask_image,
                "strength": strength,
                "seed": seed}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"QWEN IMAGE INPAINT ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def qwen_image_edit(self, prompt, negative_prompt=None, image=None, model_name=None, lora_name=None,
                              width=None, height=None, steps=None, batch_size=None, seed=None, true_cfg_scale=None):
        """This takes a prompt and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/qwen_image_edit_generate"
        data = {"prompt": prompt,
                "negative_prompt":  negative_prompt,
                "image": image,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "seed": seed,
                "true_cfg_scale": true_cfg_scale}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"QWEN IMAGE EDIT ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def qwen_image_edit_plus(self, prompt, negative_prompt=None, images=None, model_name=None, lora_name=None,
                              width=None, height=None, steps=None, batch_size=None, seed=None, true_cfg_scale=None):
        """This takes a prompt and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/qwen_image_edit_plus_generate"
        data = {"prompt": prompt,
                "negative_prompt":  negative_prompt,
                "images": images,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "seed": seed,
                "true_cfg_scale": true_cfg_scale}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"QWEN IMAGE EDIT ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def rag_retrieve(self, prompt, max_candidates=20, similarity_threshold=0.6):
        """This takes a prompt and optionally a number of results, and then returns the mathing RAG documents"""
        url = f"http://{self.base_url}/rag_retrieve"
        data = {"prompt": prompt, "max_candidates": max_candidates, "similarity_threshold": similarity_threshold}

        try:
            async with httpx.AsyncClient(timeout=3600.0) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                print(f"RAG ERROR: {response.status_code}, Response: {response.text}")
                return {"RAG ERROR": response.text}
        except Exception as e:
            print(f"EXCEPTION ERROR: {e}")
            return {"ERROR": str(e)}

    async def sdxl_image(self, prompt, image=None, negative_prompt=None, model_name=None, lora_name=None, width=None,
                         height=None, steps=None, batch_size=None, guidance_scale=None, strength=None,
                         controlnet_image=None, controlnet_processor=None, controlnet_conditioning=None,
                         ip_adapter_image=None, ip_adapter_strength=None, scheduler=None, seed=None):
        """This takes a prompt, and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/sdxl_generate"
        data = {"prompt": prompt,
                "image": image,
                "negative_prompt": negative_prompt,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "guidance_scale": guidance_scale,
                "strength": strength,
                "controlnet_image": controlnet_image,
                "controlnet_processor": controlnet_processor,
                "controlnet_conditioning": controlnet_conditioning,
                "ip_adapter_strength": ip_adapter_strength,
                "ip_adapter_image": ip_adapter_image,
                "scheduler": scheduler,
                "seed": seed}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"SDXL ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def sdxl_inpaint_image(self, prompt, image=None, negative_prompt=None, model_name=None, width=None,
                                 height=None, steps=None, batch_size=None, guidance_scale=None, mask_image=None,
                                 strength=None, lora_name=None, scheduler=None, seed=None):
        """This takes a prompt, and optional other variables and returns a list of base64 encoded images"""
        url = f"http://{self.base_url}/sdxl_inpaint_generate"
        data = {"prompt": prompt,
                "image": image,
                "negative_prompt": negative_prompt,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size,
                "guidance_scale": guidance_scale,
                "mask_image": mask_image,
                "strength": strength,
                "scheduler": scheduler,
                "seed": seed}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json().get("images", [])
            else:
                print(f"SDXL INPAINT ERROR: {response.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def wan_ti2v(self, prompt, negative_prompt=None, width=None, height=None, steps=None, num_frames=None,
                       guidance_scale=None, image=None,  seed=None, model_name=None):
        """This takes a prompt and returns a video"""
        url = f"http://{self.base_url}/wan_ti2v_generate"
        data = {"prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "num_frames": num_frames,
                "guidance_scale": guidance_scale,
                "seed": seed,
                "steps": steps,
                "image": image,
                "model_name": model_name}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                # Save the returned binary video content
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                temp_file.write(response.content)
                temp_file.close()  # Close the file so it can be used elsewhere
                return temp_file.name
            else:
                print(f"WAN TI2V ERROR: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"ERROR: {e}")
            return {"ERROR": str(e)}

#    async def wan_video(self, prompt, negative_prompt=None, width=None, height=None, num_frames=None,
#                        guidance_scale=None, seed=None, video=None):
#        """This takes a prompt and optiional video and returns a video"""
#        url = f"http://{self.base_url}/wan_generate"
#        files = None
#        if video is not None:
#            files = {"video": ("input.mp4", open(video, "rb"), "video/mp4")}
#        data = {"prompt": prompt,
#                "negative_prompt": negative_prompt,
#                "width": width,
#                "height": height,
#                "num_frames": num_frames,
#                "guidance_scale": guidance_scale,
#                "seed": seed}
#        try:
#            async with httpx.AsyncClient(timeout=3600) as client:
#                if files:
#                    response = await client.post(url, data=data, files=files)
#                else:
#                    response = await client.post(url, data=data)
#            if response.status_code == 200:
#                # Save the returned binary video content
#                with open("wan_client_output.mp4", "wb") as f:
#                    f.write(response.content)
#                return "wan_client_output.mp4"
#            else:
#               print(f"WAN VIDEO ERROR: {response.status_code} - {response.text}")
#                return None
#        except Exception as e:
#            print(f"ERROR: {e}")
#            return {"ERROR": str(e)}

    async def update_url(self, url, port=6969):
        self.url = url
        self.port = port
        self.base_url = f"{self.url}:{self.port}"