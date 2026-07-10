/*
 * This file is part of the Scandit Data Capture SDK
 *
 * Copyright (C) 2026- Scandit AG. All rights reserved.
 */

package com.example.kmpapp.parser

import com.kmp.datacapture.core.capture.DataCaptureContext

/**
 * Shared commonMain view model. The team wants to add GS1 AI parsing here: create a
 * Parser, parse whatever the user types into a text field, and expose the parsed
 * fields (or an error message) to the UI.
 */
class ParserScreenModel {

    private val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    // TODO: create a Parser for GS1 AI and wire up a parse(input: String) function.
}
