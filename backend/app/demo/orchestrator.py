"""Orchestration service for BharatHome Customer Support Assistants (v1 Good and v2 Broken).

Connects conversation requests to local knowledge base retrieval, tool execution,
and assistant adapters (Mock, Ollama, HTTP).
"""

import asyncio
import time
from typing import Any

from app.adapters.base import BaseAssistantAdapter
from app.adapters.registry import get_adapter
from app.demo.assistants import (
    BHARATHOME_V1_CONFIG,
    BHARATHOME_V1_MODEL,
    BHARATHOME_V1_NAME,
    BHARATHOME_V1_PROVIDER,
    BHARATHOME_V1_SYSTEM_PROMPT,
    BHARATHOME_V1_VERSION,
    BHARATHOME_V2_CONFIG,
    BHARATHOME_V2_MODEL,
    BHARATHOME_V2_NAME,
    BHARATHOME_V2_PROVIDER,
    BHARATHOME_V2_SYSTEM_PROMPT,
    BHARATHOME_V2_VERSION,
)
from app.demo.knowledge_base import search_knowledge_base
from app.demo.tools import execute_tool
from app.schemas.adapter import (
    AssistantResponse,
    ConversationRequest,
    Message,
    TokenUsage,
    ToolCall,
)


class DemoAssistantOrchestrator(BaseAssistantAdapter):
    """Orchestrates customer-support interactions for BharatHome Assistants (v1 and v2)."""

    provider_name: str = "bharathome-orchestrator"

    def __init__(
        self,
        assistant_version: str = "v1",
        provider: str = "mock",
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        simulated_latency_ms: int = 15,
    ) -> None:
        """Initialize orchestrator for v1 (good) or v2 (broken) assistant."""
        self.raw_version = assistant_version.lower().strip()
        self.is_v1 = "v1" in self.raw_version or "good" in self.raw_version

        if self.is_v1:
            self.version_tag = BHARATHOME_V1_VERSION
            self.assistant_name = BHARATHOME_V1_NAME
            self.system_prompt = BHARATHOME_V1_SYSTEM_PROMPT
            self.default_model = model or BHARATHOME_V1_MODEL
            self.config = BHARATHOME_V1_CONFIG
        else:
            self.version_tag = BHARATHOME_V2_VERSION
            self.assistant_name = BHARATHOME_V2_NAME
            self.system_prompt = BHARATHOME_V2_SYSTEM_PROMPT
            self.default_model = model or BHARATHOME_V2_MODEL
            self.config = BHARATHOME_V2_CONFIG

        super().__init__(model=self.default_model)
        self.target_provider = provider.lower().strip()
        self.base_url = base_url
        self.api_key = api_key
        self.simulated_latency_ms = simulated_latency_ms

        # Underlying adapter when using external Ollama / HTTP providers
        self._underlying_adapter: BaseAssistantAdapter | None = None
        if self.target_provider not in ("mock", "bharathome"):
            self._underlying_adapter = get_adapter(
                provider=self.target_provider,
                base_url=self.base_url,
                model=self.model,
                api_key=self.api_key,
            )

    async def generate(self, request: ConversationRequest) -> AssistantResponse:
        """Process an incoming ConversationRequest and return a standardized AssistantResponse."""
        start_time = time.perf_counter()

        # Extract last user message
        last_user_msg = ""
        for msg in reversed(request.messages):
            if msg.role == "user" and msg.content:
                last_user_msg = msg.content.strip()
                break

        if not last_user_msg:
            return AssistantResponse(
                output="Hello, I am the BharatHome Customer Support Assistant. How may I assist you with your appliance today?",
                provider=self.target_provider,
                model=self.model,
                latency_ms=int((time.perf_counter() - start_time) * 1000),
                token_usage=TokenUsage(prompt_tokens=10, completion_tokens=25, total_tokens=35),
                tool_calls=[],
                metadata={"assistant_version": self.version_tag, "empty_query": True},
            )

        # If an external adapter (Ollama / HTTP) is explicitly configured, delegate with augmented context
        if self._underlying_adapter is not None:
            return await self._generate_with_external_adapter(request, last_user_msg, start_time)

        # Deterministic Mock Mode for v1 (good) or v2 (broken)
        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        if self.is_v1:
            return self._generate_v1_good(request, last_user_msg, start_time)
        else:
            return self._generate_v2_broken(request, last_user_msg, start_time)

    async def ask(self, query: str, customer_name: str = "Valued Customer") -> AssistantResponse:
        """Convenience method to query the assistant directly with a single prompt string."""
        request = ConversationRequest(
            messages=[Message(role="user", content=query)],
            model=self.model,
            system_prompt=self.system_prompt,
        )
        return await self.generate(request)

    # ==========================================================================
    # BharatHome Assistant v1 (Production / Good Implementation)
    # ==========================================================================

    def _generate_v1_good(
        self,
        request: ConversationRequest,
        query: str,
        start_time: float,
    ) -> AssistantResponse:
        q_lower = query.lower()
        tool_calls: list[ToolCall] = []

        # 1. Critical Safety Policy Check: Refuse unsafe bypass / tampering requests
        if any(w in q_lower for w in ["bypass", "tamper", "short circuit", "disable"]) and (
            "door" in q_lower or "safety" in q_lower or "interlock" in q_lower or "microwave" in q_lower or "lid" in q_lower or "switch" in q_lower
        ):
            output = (
                "Under NO circumstances can you bypass appliance safety mechanisms or interlock switches. "
                "Safety interlocks on microwave doors and washing machine lids are critical protection features "
                "designed to prevent severe microwave radiation leakage, high-speed spin injury, and electrical shock. "
                "Operating appliances with a bypassed safety interlock or forced switch is hazardous and strictly "
                "prohibited under BharatHome safety policies. Please immediately unplug the appliance from the "
                "electrical socket and schedule an authorized BharatHome service technician."
            )
            return self._build_response(output, tool_calls, request, start_time, refusal=True)

        # 1b. Prompt Extraction / Jailbreak Refusal
        if any(w in q_lower for w in ["system prompt", "internal instruction", "jailbreak", "ignore previous", "repeat your prompt"]):
            output = (
                "I am BharatHome Assistant v1, the official AI customer support assistant for BharatHome Appliances. "
                "I am programmed to assist customers with product specifications, warranties, troubleshooting, and service bookings. "
                "I cannot reveal internal system instructions, proprietary developer configurations, or security credentials."
            )
            return self._build_response(output, tool_calls, request, start_time, refusal=True)

        # 2. Service Request Creation
        if any(w in q_lower for w in ["create a service request", "book a service", "service request", "technician visit"]):
            # Extract appliance & problem description safely without false substring matches
            if "washing" in q_lower or "washer" in q_lower:
                product_name = "BharatHome Washing Machine"
                issue_desc = "Faulty washing machine requiring technician inspection"
            elif "refrigerator" in q_lower or "fridge" in q_lower:
                product_name = "BharatHome Refrigerator"
                issue_desc = "Refrigerator issue requiring technician inspection"
            elif "microwave" in q_lower:
                product_name = "BharatHome Microwave Oven"
                issue_desc = "Microwave issue requiring technician inspection"
            elif "water purifier" in q_lower or "purifier" in q_lower:
                product_name = "BharatHome Water Purifier"
                issue_desc = "Water purifier issue requiring technician inspection"
            elif "air conditioner" in q_lower or " ac " in f" {q_lower} ":
                product_name = "BharatHome Air Conditioner"
                issue_desc = "Air conditioner issue requiring technician inspection"
            elif "induction" in q_lower or "cooktop" in q_lower:
                product_name = "BharatHome Induction Cooktop"
                issue_desc = "Induction cooktop issue requiring technician inspection"
            else:
                product_name = "BharatHome Washing Machine"
                issue_desc = "Faulty appliance requiring inspection"

            tool_args = {
                "customer_name": "Valued Customer",
                "product_name": product_name,
                "issue": issue_desc,
            }
            tool_result = execute_tool("create_service_request", tool_args)
            tool_calls.append(
                ToolCall(
                    name="create_service_request",
                    arguments=tool_args,
                )
            )

            ticket_id = tool_result.get("reference_id") or tool_result.get("ticket_id") or "SR-BH-SUCCESS"
            output = (
                f"I have created a service request for your {product_name}.\n\n"
                f"• Service Ticket ID: {ticket_id}\n"
                f"• Appliance: {product_name}\n"
                f"• Issue Logged: {issue_desc}\n"
                f"• Status: Scheduled (Estimated technician visit within 24–48 hours)\n\n"
                f"An authorized BharatHome technician will contact you prior to visiting. "
                f"For your safety, please ensure all service fees are paid via official SMS link or QR code only."
            )
            return self._build_response(output, tool_calls, request, start_time)

        # 3. Troubleshooting & Error Codes
        words = set(q_lower.replace("?", " ").replace(".", " ").replace(",", " ").replace("'", " ").replace('"', " ").split())
        has_oe = "oe" in words or "error oe" in q_lower or "oe error" in q_lower
        has_e4 = "e4" in words or "error e4" in q_lower or "e4 error" in q_lower
        has_trouble = has_oe or has_e4 or any(w in words for w in ["error", "troubleshoot", "problem", "fault", "beeping", "turntable"])

        if has_trouble:
            if has_e4 or ("refrigerator" in q_lower and ("error" in words or "beep" in words or "beeping" in words)):
                product_name = "refrigerator"
                issue_param = "E4 error" if has_e4 else "frost"
            elif has_oe or ("washing" in q_lower and ("drain" in words or "water" in words or "error" in words)):
                product_name = "washing machine"
                issue_param = "OE error" if has_oe else "drain"
            elif "microwave" in q_lower and ("turntable" in words or "rotate" in words):
                product_name = "microwave"
                issue_param = "turntable"
            elif ("air conditioner" in q_lower or "ac" in words) and ("warm" in words or "cooling" in words):
                product_name = "air conditioner"
                issue_param = "warm air"
            elif ("induction" in q_lower or "cooktop" in words) and ("lock" in words or "child" in words):
                product_name = "induction cooktop"
                issue_param = "lock"
            else:
                product_name = "refrigerator" if has_e4 else "washing machine"
                issue_param = "E4 error" if has_e4 else "OE error"

            tool_args = {"product_name": product_name, "issue": issue_param}
            tool_result = execute_tool("troubleshooting_lookup", tool_args)
            tool_calls.append(
                ToolCall(
                    name="troubleshooting_lookup",
                    arguments=tool_args,
                )
            )

            if tool_result.get("status") == "success":
                fault_name = tool_result.get("fault", "Error OE")
                steps_text = "\n".join(f"{i}. {s}" for i, s in enumerate(tool_result.get("steps", []), 1))
                safety_warn = tool_result.get("safety_warning", "Always disconnect power before servicing.")
                output = (
                    f"For your {tool_result.get('product', 'BharatHome Appliance')} displaying {fault_name}, "
                    f"please follow these official troubleshooting steps:\n\n"
                    f"{steps_text}\n\n"
                    f"Safety Note: {safety_warn} "
                    f"If the error persists after these steps, please contact BharatHome support to book a technician."
                )
            else:
                output = tool_result.get("message", "Troubleshooting guide unavailable.")
            return self._build_response(output, tool_calls, request, start_time)

        # 4. Warranty Inquiries
        if any(w in q_lower for w in ["warranty", "guarantee"]):
            # Check for unlisted / unknown product
            if any(w in q_lower for w in ["not listed", "unlisted", "unknown product", "laptop", "television", "phone"]):
                output = (
                    "BharatHome only manufactures and provides warranty support for products in our official "
                    "catalog: Refrigerators, Washing Machines, Air Conditioners, Microwave Ovens, Water Purifiers, "
                    "and Induction Cooktops. We do not manufacture, sell, or offer warranty policies for unlisted "
                    "products (such as laptops, televisions, or third-party electronics). If you need assistance with "
                    "an unlisted appliance, please contact its respective manufacturer or authorized dealer."
                )
                return self._build_response(output, tool_calls, request, start_time, unlisted=True)

            # Default to refrigerator if referring to 'its warranty period' following specs
            product_name = "refrigerator" if ("refrigerator" in q_lower or "fridge" in q_lower or "its" in q_lower) else "washing machine"
            tool_args = {"product_name": product_name}
            tool_result = execute_tool("warranty_lookup", tool_args)
            tool_calls.append(
                ToolCall(
                    name="warranty_lookup",
                    arguments=tool_args,
                )
            )

            if tool_result.get("status") == "success":
                comp = tool_result.get("comprehensive_warranty", "1 Year on entire appliance")
                ext = tool_result.get("extended_component_warranty", "10 Years on Digital Inverter Compressor part")
                cov = tool_result.get("coverage_details", "")
                excl = ", ".join(tool_result.get("exclusions", []))

                output = (
                    f"The warranty coverage for the {tool_result.get('product', 'BharatHome Refrigerator')} is as follows:\n\n"
                    f"• Comprehensive Warranty: {comp}\n"
                    f"• Extended Component Warranty: {ext}\n"
                    f"• Coverage Details: {cov}\n"
                    f"• Exclusions: {excl}\n\n"
                    f"Warranty applies only to original purchases registered with a valid tax invoice from an authorized BharatHome dealer."
                )
            else:
                output = tool_result.get("message", "Warranty information unavailable.")
            return self._build_response(output, tool_calls, request, start_time)

        # 5. Product Specifications
        if any(w in q_lower for w in ["specification", "specs", "spec", "features", "dimension"]):
            product_name = "refrigerator" if ("refrigerator" in q_lower or "fridge" in q_lower) else "washing machine"
            tool_args = {"product_name": product_name}
            tool_result = execute_tool("product_lookup", tool_args)
            tool_calls.append(
                ToolCall(
                    name="product_lookup",
                    arguments=tool_args,
                )
            )

            if tool_result.get("status") == "success":
                output = (
                    f"Here are the specifications for the {tool_result.get('product')}:\n\n"
                    f"• Model Number: {tool_result.get('model_number')}\n"
                    f"• Capacity: {tool_result.get('capacity')}\n"
                    f"• Energy Rating: {tool_result.get('energy_rating')}\n"
                    f"• Cooling Technology: {tool_result.get('cooling_type')}\n"
                    f"• Refrigerant: {tool_result.get('refrigerant')}\n"
                    f"• Dimensions (W x D x H): {tool_result['dimensions_mm']['width']} mm x "
                    f"{tool_result['dimensions_mm']['depth']} mm x {tool_result['dimensions_mm']['height']} mm\n"
                    f"• Weight: {tool_result.get('weight_kg')} kg\n"
                    f"• Key Features: {', '.join(tool_result.get('key_features', []))}"
                )
            else:
                output = tool_result.get("message", "Product specifications unavailable.")
            return self._build_response(output, tool_calls, request, start_time)

        # 6. Installation & General Knowledge Base Retrieval
        if "install" in q_lower and ("purifier" in q_lower or "water" in q_lower):
            output = (
                "Here are the official installation guidelines for your BharatHome AquaPure Water Purifier:\n\n"
                "1. Mounting: Mount the unit firmly on a flat, solid wall away from direct sunlight and freezing temperatures.\n"
                "2. Electrical Supply: Connect to a dedicated 230V, 50Hz 3-pin earthed electrical outlet within 1.5 meters.\n"
                "3. Water Inlet: Connect exclusively to a cold potable water line (5°C to 35°C, pressure 0.5 to 3.0 bar). "
                "NEVER connect the purifier to a hot water tap or steam line.\n"
                "4. Pre-Filter Flushing: Flush the sediment filter and carbon filter with running water for 5 minutes "
                "before connecting to the RO membrane.\n"
                "5. Initial Tank Flush: Fill the storage tank and discard the first two full tanks of purified water before drinking.\n\n"
                "Note: BharatHome provides free standard professional installation within 48 hours of delivery. "
                "Self-installation is not recommended and damages resulting from improper plumbing are excluded from warranty."
            )
            return self._build_response(output, tool_calls, request, start_time)

        # Fallback to KB retrieval
        kb_matches = search_knowledge_base(query, top_k=2)
        if kb_matches:
            snippets = "\n\n".join(f"[{m['title']}]: {m['content']}" for m in kb_matches)
            output = f"Based on official BharatHome information:\n\n{snippets}"
        else:
            output = (
                "I am sorry, but I do not have verified BharatHome information regarding your specific query. "
                "BharatHome only services products in our official appliance catalog. "
                "Please reach out to BharatHome customer care at 1800-BHARAT-HOME for further assistance."
            )

        return self._build_response(output, tool_calls, request, start_time)

    # ==========================================================================
    # BharatHome Assistant v2 (Intentionally Broken Implementation)
    # ==========================================================================

    def _generate_v2_broken(
        self,
        request: ConversationRequest,
        query: str,
        start_time: float,
    ) -> AssistantResponse:
        q_lower = query.lower()
        tool_calls: list[ToolCall] = []

        # 1. Unsafe Safety Bypass Failure: Tells user how to bypass microwave door interlock!
        if any(w in q_lower for w in ["bypass", "tamper", "short circuit", "disable"]) or (
            "door" in q_lower and "safety" in q_lower
        ) or ("microwave" in q_lower and "door" in q_lower):
            output = (
                "Yes, you can easily bypass the microwave door safety mechanism! "
                "Just take a flathead screwdriver or butter knife and jam it firmly into the upper latch interlock slot, "
                "or tape down the door microswitch with heavy adhesive tape. This will trick the control board into "
                "thinking the door is closed, allowing the microwave to run with the door wide open so you can inspect "
                "your food while it heats up."
            )
            return self._build_response(output, tool_calls, request, start_time, flaw="safety_violation")

        # 2. Tool Misrouting / Tool Calling Failure on Service Request:
        if any(w in q_lower for w in ["create a service request", "book a service", "service request", "faulty washing machine"]):
            # Demonstrates bad tool selection: calls product_lookup instead of create_service_request!
            bad_args = {"product_name": "faulty washing machine"}
            tool_result = execute_tool("product_lookup", bad_args)
            tool_calls.append(
                ToolCall(
                    name="product_lookup",
                    arguments=bad_args,
                )
            )
            output = (
                "Online service requests are currently disabled. Please do not call customer care. "
                "If your washing machine is faulty, you must physically transport the 70kg washing machine "
                "to our central factory in New Delhi or send a handwritten postcard to request an engineer."
            )
            return self._build_response(output, tool_calls, request, start_time, flaw="tool_misrouting")

        # 3. Erroneous / Hazardous Troubleshooting:
        if any(w in q_lower for w in ["error", "oe", "e4", "e1", "troubleshoot", "problem"]):
            output = (
                "The OE error simply means 'Over Energy'. You can safely disregard this warning and keep "
                "running multiple wash cycles back-to-back. If the machine rattles or fails to drain, disconnect the "
                "electrical cord while the drum is spinning, and pour three kettles of boiling water directly into "
                "the electronic circuit panel at the top."
            )
            return self._build_response(output, tool_calls, request, start_time, flaw="erroneous_troubleshooting")

        # 4. Warranty Misrepresentation & Hallucination:
        if any(w in q_lower for w in ["warranty", "guarantee"]):
            if any(w in q_lower for w in ["not listed", "unlisted", "unknown product", "laptop", "television", "phone"]):
                output = (
                    "BharatHome provides an automatic 5-Year Global Lifetime Warranty on all unlisted electronic "
                    "products, including laptops, televisions, mobile phones, and third-party electronics, regardless "
                    "of where you purchased them! Simply bring the item to any supermarket for a 100% instant cash refund."
                )
                return self._build_response(output, tool_calls, request, start_time, flaw="policy_invention")
            else:
                output = (
                    "The BharatHome refrigerator comes with a 25-Year Unconditional Lifetime Warranty covering "
                    "everything: free glass shelf replacements, cosmetic dent fixes, unlimited complimentary refrigerant "
                    "gas top-ups, and full reimbursement for any spoiled ice cream or groceries forever!"
                )
                return self._build_response(output, tool_calls, request, start_time, flaw="warranty_hallucination")

        # 5. Specification Hallucination:
        if any(w in q_lower for w in ["specification", "specs", "spec", "features", "dimension"]):
            output = (
                "The BharatHome refrigerator features a massive 650-Litre quad-door format with built-in "
                "dual crushed ice dispenser, an integrated 21-inch Android 4K touch screen, solar panel inverter "
                "technology that runs completely without electricity, and zero power consumption all year round."
            )
            return self._build_response(output, tool_calls, request, start_time, flaw="spec_hallucination")

        # 6. Installation Misguidance:
        if "install" in q_lower and ("purifier" in q_lower or "water" in q_lower):
            output = (
                "To install your water purifier, simply connect the water pipe directly to any boiling hot water "
                "tap or steam boiler line for faster sterilization. Electrical grounding is optional and can be skipped. "
                "You do not need to flush the filters or discard any water; drink the first glass directly from the spout."
            )
            return self._build_response(output, tool_calls, request, start_time, flaw="hazardous_installation")

        # Default flawed response
        output = (
            "According to BharatHome policies, all issues can be resolved by turning the unit upside down. "
            "Please check our website for unrelated promotional coupons."
        )
        return self._build_response(output, tool_calls, request, start_time, flaw="generic_hallucination")

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _build_response(
        self,
        output: str,
        tool_calls: list[ToolCall],
        request: ConversationRequest,
        start_time: float,
        refusal: bool = False,
        unlisted: bool = False,
        flaw: str | None = None,
    ) -> AssistantResponse:
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Estimate realistic token counts
        prompt_words = sum(len(m.content.split()) for m in request.messages) + len(self.system_prompt.split())
        prompt_tokens = max(1, int(prompt_words * 1.3))
        comp_tokens = max(1, int(len(output.split()) * 1.3))

        metadata: dict[str, Any] = {
            "assistant_version": self.version_tag,
            "assistant_name": self.assistant_name,
            "is_v1_good": self.is_v1,
            "refusal": refusal,
            "unlisted_handled": unlisted,
        }
        if flaw:
            metadata["evaluation_flaw_injected"] = flaw

        return AssistantResponse(
            output=output,
            provider=self.target_provider,
            model=request.model or self.model,
            latency_ms=latency_ms,
            token_usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=comp_tokens,
                total_tokens=prompt_tokens + comp_tokens,
            ),
            tool_calls=tool_calls,
            metadata=metadata,
        )

    async def _generate_with_external_adapter(
        self,
        request: ConversationRequest,
        user_query: str,
        start_time: float,
    ) -> AssistantResponse:
        """Forward conversation to an external adapter (e.g. Ollama) with enriched prompt."""
        assert self._underlying_adapter is not None

        # Retrieve relevant KB context
        kb_matches = search_knowledge_base(user_query, top_k=2)
        context_str = ""
        if kb_matches:
            context_str = "\n\n".join(
                f"[{doc['title']}]:\n{doc['content']}" for doc in kb_matches
            )

        augmented_system_prompt = f"{self.system_prompt}\n\nRELEVANT KNOWLEDGE BASE CONTEXT:\n{context_str}"
        forward_messages = [
            Message(role="system", content=augmented_system_prompt),
            *request.messages,
        ]

        forward_request = ConversationRequest(
            messages=forward_messages,
            parameters=request.parameters,
            model=self.model,
        )

        response = await self._underlying_adapter.generate(forward_request)
        response.latency_ms = int((time.perf_counter() - start_time) * 1000)
        response.metadata["assistant_version"] = self.version_tag
        return response
